from dataclasses import dataclass
import os
import shutil
from models import *

REGISTRY_ADDRESS = "130.191.161.13:5000"

def __create_dockerfile():
    f = open("dockerfile", "w")
    f.write("FROM python:3.11.5\n")
    f.write("WORKDIR /code\n")
    f.write("COPY requirements.txt .\n")
    f.write("RUN pip install -r requirements.txt\n")
    f.write("COPY src/ .\n")
    f.write("CMD [ \"python\", \"./main.py\" ]")
    f.close()

def __generate_image(container: Container):
    # remove remnants of previous container
    try:
        shutil.rmtree("src/")
    except:
        pass
    try:
        os.remove("requirements.txt")
    except:
        pass

    # copy container files to build directory
    shutil.copytree(container.src_dir, "src/")
    shutil.copy(container.python_requirements, "requirements.txt")

    # build and push container image
    os.system(f"docker buildx build --push --platform linux/arm64,linux/amd64 --tag {REGISTRY_ADDRESS}/registry/{container.registry_tag} . --output=type=registry,registry.insecure=true")

def __create_yaml(namespace: str, containers: list):
    file = open("generated.yaml", "w")
    file.write("apiVersion: v1\n")
    file.write("kind: Namespace\n")
    file.write("metadata:\n")
    file.write(f"  name: {namespace}\n")
    file.write("---\n")
    for container in containers:
        file.write("apiVersion: apps/v1\n")
        file.write("kind: Deployment\n")
        file.write("metadata:\n")
        file.write("  labels:\n")
        file.write(f"    k8s-app: {container.registry_tag}\n")
        file.write(f"  name: {container.registry_tag}\n")
        file.write(f"  namespace: {namespace}\n")
        file.write("spec:\n")
        file.write("  selector:\n")
        file.write("    matchLabels:\n")
        file.write(f"      k8s-app: {container.registry_tag}\n")
        file.write(f"  replicas: 1\n")
        file.write("  template:\n")
        file.write("    metadata:\n")
        file.write("      labels:\n")
        file.write(f"        k8s-app: {container.registry_tag}\n")
        file.write("    spec:\n")
        file.write("      containers:\n")
        file.write(f"      - name: {container.registry_tag}\n")
        file.write(f"        image: {REGISTRY_ADDRESS}/{namespace}/{container.registry_tag}\n")
        file.write("        imagePullPolicy: Always\n")
        file.write("        ports:\n")
        for port in container.ports:
            file.write(f"        - containerPort: {port}\n")
        file.write("---\n")

def deploy_experiment(experiment: Experiment):
    __create_dockerfile()

    containers = []

    with open("helper-app/smile_app.py", "w") as f:
        f.seek(0,0)
        f.write(f"EXPERIMENT_UUID = {experiment.experiment_uuid}")

    smile_container = Container(src_dir="helper-app/src/", python_requirements="helper-app/requirements.txt", registry_tag=experiment.created_by, ports=[5555], status=ContainerStatus.PENDING)
    __generate_image(smile_container)
    containers.append(smile_container)

    for node in experiment.nodes:
        for container in node.containers:
            __generate_image(container)
            containers.append(container)

    __create_yaml(experiment.created_by, containers)
    os.system("sudo k3s kubectl create -f generated.yaml")