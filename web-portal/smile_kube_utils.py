from dataclasses import dataclass
import os
import subprocess
import shutil

REGISTRY_ADDRESS = "130.191.161.13:5000"

@dataclass
class Port:
    port: int
    node_port: int
    protocol: str = "TCP"


@dataclass
class Application:
    src_dir: str
    requirements: str
    registry_tag: str
    ports: list
    redundant_instances: int = 1

def create_dockerfile():
    f = open("dockerfile", "w")
    f.write("FROM python:3.11.5\n")
    f.write("WORKDIR /code\n")
    f.write("COPY requirements.txt .\n")
    f.write("RUN pip install -r requirements.txt\n")
    f.write("COPY src/ .\n")
    f.write("CMD [ \"python\", \"./main.py\" ]")
    f.close()

def generate_images(applications: list):
    create_dockerfile()
    for app in applications:
        try:
            shutil.rmtree("src/")
        except:
            pass
        try:
            os.remove("requirements.txt")
        except:
            pass
        shutil.copytree(app.src_dir, "src/")
        shutil.copy(app.requirements, "requirements.txt")
        os.system(f"./start.sh {REGISTRY_ADDRESS} {app.registry_tag}")

def create_yaml(namespace: str, applications: list):
    file = open("generated.yaml", "w")
    file.write("apiVersion: v1\n")
    file.write("kind: Namespace\n")
    file.write("metadata:\n")
    file.write(f"  name: {namespace}\n")
    file.write("---\n")
    for application in applications:
        file.write("apiVersion: apps/v1\n")
        file.write("kind: Deployment\n")
        file.write("metadata:\n")
        file.write("  labels:\n")
        file.write(f"    k8s-app: {application.registry_tag}\n")
        file.write(f"  name: {application.registry_tag}\n")
        file.write(f"  namespace: {namespace}\n")
        file.write("spec:\n")
        file.write("  selector:\n")
        file.write("    matchLabels:\n")
        file.write(f"      k8s-app: {application.registry_tag}\n")
        file.write(f"  replicas: {application.redundant_instances}\n")
        file.write("  template:\n")
        file.write("    metadata:\n")
        file.write("      labels:\n")
        file.write(f"        k8s-app: {application.registry_tag}\n")
        file.write("    spec:\n")
        file.write("      containers:\n")
        file.write(f"      - name: {application.registry_tag}\n")
        file.write(f"        image: {REGISTRY_ADDRESS}/registry/{application.registry_tag}\n")
        file.write("        imagePullPolicy: Always\n")
        file.write("---\n")
        file.write("apiVersion: v1\n")
        file.write("kind: Service\n")
        file.write("metadata:\n")
        file.write("  labels:\n")
        file.write(f"    k8s-app: {application.registry_tag}-svc\n")
        file.write(f"  name: {application.registry_tag}-svc\n")
        file.write(f"  namespace: {namespace}\n")
        file.write("spec:\n")
        file.write("  type: NodePort\n")
        file.write("  selector:\n")
        file.write(f"    k8s-app: {application.registry_tag}\n")
        file.write("  ports:\n")
        i = 0
        for port in application.ports:
            file.write(f"  - name: port{i}\n")
            file.write(f"    nodePort: {port.node_port}\n")
            file.write(f"    port: {port.port}\n")
            file.write(f"    protocol: {port.protocol}\n")
            i += 1
        file.write("---\n")

apps =[]
apps.append(Application(
    src_dir='/home/e302d/Desktop/dockerpython/dockerHost/uploads/app0/src/',
    requirements='/home/e302d/Desktop/dockerpython/dockerHost/uploads/app0/requirements.txt',
    registry_tag='app0',
    ports=[Port(port=5006, node_port=31006)]))
            
apps.append(Application(
    src_dir='/home/e302d/Desktop/dockerpython/dockerHost/uploads/app1/src/',
    requirements='/home/e302d/Desktop/dockerpython/dockerHost/uploads/app1/requirements.txt',
    registry_tag='app1',
    ports=[Port(port=5005, node_port=31005)]))

if __name__ == "__main__":
    generate_images(apps)
    create_yaml("testingnamespcace", apps)
    os.system("sudo k3s kubectl create -f generated.yaml")