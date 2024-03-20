import os
import shutil
from models import *
import yaml
import kubernetes
import random
import subprocess

REGISTRY_ADDRESS = "130.191.161.13:5000"

kubernetes.config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
core_v1 = kubernetes.client.CoreV1Api()
batch_v1 = kubernetes.client.BatchV1Api()


kubernetes_nodes: list[KubernetesNode] = []


def __create_dockerfile():
    f = open("dockerfile", "w")
    f.write("FROM python:3.11.5\n")
    f.write("WORKDIR /code\n")
    f.write("COPY requirements.txt .\n")
    f.write("RUN apt update\n")
    f.write("RUN apt install -y jq\n")
    f.write("RUN pip install -r requirements.txt\n")
    f.write("COPY src/ .\n")
    f.write("CMD [ \"./start.sh\" ]")
    f.close()


def __generate_image(experiment: Experiment, container: Container):
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
    shutil.copy("../smile-module/start.sh", "src/start.sh")

    with open("src/start.sh", "r") as f:
        lines = f.readlines()
    
    with open("src/start.sh", "w") as f:
        lines[2] = f"experiment_id=\"{experiment.experiment_uuid}\"\n"
        lines[3] = f"container_id=\"{container.registry_tag}\"\n"
        f.writelines(lines)

    # build and push container image
    os.system(f"docker buildx build --push --platform linux/arm64,linux/amd64 --tag {REGISTRY_ADDRESS}/{experiment.created_by}/{container.registry_tag} . --output=type=registry,registry.insecure=true")


def __create_yaml(experiment: Experiment, containers: list[Container]):
    documents = [{
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": experiment.created_by
        }
    }]
    
    # Loop through each container to create Jobs
    for container in containers:
        job_document = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": container.name,
                "namespace": experiment.created_by,
                "labels": {
                    "k8s-app": container.name
                },
            },
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {
                            "k8s-app": container.name
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": container.name,
                            "image": f"{REGISTRY_ADDRESS}/{experiment.created_by}/{container.registry_tag}",
                            "imagePullPolicy": "Always"
                        }],
                        "restartPolicy": "Never",
                        "nodeName": f"{container.hostname}"
                    }
                },
                "backoffLimit": 0
            }
        }
        documents.append(job_document)
        
        # Service document if container has ports
        if len(container.ports) > 0:
            service_document = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": f"{container.name}-svc",
                    "namespace": experiment.created_by,
                    "labels": {
                        "k8s-app": f"{container.name}-svc"
                    },
                },
                "spec": {
                    "selector": {
                        "k8s-app": container.name
                    },
                    "ports": [{"port": port} for port in container.ports]
                }
            }
            documents.append(service_document)
        
    # Write to YAML file
    with open("generated.yaml", "w") as file:
        yaml.dump_all(documents, file)


def __select_random_node(node_type: NodeType):
    for kubernetes_node in kubernetes_nodes:
        if kubernetes_node.type == node_type:
            return kubernetes_node
    return ""


def deploy_experiment(experiment: Experiment):
    os.system(f"sudo k3s kubectl delete namespace {experiment.created_by}")
    print("creating dockerfile...", end=" ")
    __create_dockerfile()
    print("done")

    containers = []

    # Create RAPTURE SMILE app
    with open("../rapture-smile-app/src/main.py", "r") as f:
        lines = f.readlines()
    with open("../rapture-smile-app/src/main.py", "w") as f:
        lines[0] = f"EXPERIMENT_UUID = \"{experiment.experiment_uuid}\"\n"
        f.writelines(lines)
    rapture_smile_app = Container(src_dir="../rapture-smile-app/src/", python_requirements="../rapture-smile-app/requirements.txt",
                                registry_tag=f"rapture-smile-app-{experiment.experiment_uuid}", ports=[5555],
                                status=ContainerStatus.PENDING, name=f"rapture-smile-app-{experiment.experiment_uuid}",
                                hostname=__select_random_node(NodeType.COMPUTE_PI))
    print("creating Rapture Smile App image...", end=" ")
    __generate_image(experiment, rapture_smile_app)
    print("done")
    containers.append(rapture_smile_app)

    for node in experiment.nodes:
        if node.type == NodeType.ROVER_PI:
            with open("../rover-smile-app/src/main.py", "r") as f:
                lines = f.readlines()
            with open("../rover-smile-app/src/main.py", "w") as f:
                lines[0] = f"ROBOT_NAME = \"{node.kubernetes_node.hostname}\"\n"
                f.writelines(lines)
            rover_smile_app = Container(src_dir="../rover-smile-app/src/", python_requirements="../rover-smile-app/requirements.txt",
                                        registry_tag=f"{node.kubernetes_node.hostname}-rover-smile-app-{experiment.experiment_uuid}", ports=[5555],
                                        status=ContainerStatus.PENDING, name=f"{node.kubernetes_node.hostname}-rover-smile-app-{experiment.experiment_uuid}",
                                        hostname=node.kubernetes_node.hostname)
            print(f"creating Rover Smile App image for {node.kubernetes_node.hostname}...", end=" ")
            __generate_image(experiment, rover_smile_app)
            print("done")
            containers.append(rover_smile_app)

    # Create user apps
    used_nodes = []
    for node in experiment.nodes:
        if node.kubernetes_node == None:
            kubernetes_node = None
            while True:
                kubernetes_node = __select_random_node(node.type)
                if kubernetes_node not in used_nodes:
                    break
            used_nodes.append(kubernetes_node)
            node.kubernetes_node = kubernetes_node
        for container in node.containers:
            container.hostname = node.kubernetes_node.hostname
            print(f"creating user {container.name} App image...", end=" ")
            with open(container.src_dir + "/smile.py", "a") as f:
                f.write(f"\n__init(\"{experiment.created_by}\")")
            __generate_image(experiment, container)
            print("done")
            containers.append(container)

    print("creating k3s deployment yaml...", end=" ")
    __create_yaml(experiment, containers)
    print("done")
    print("deploying...", end=" ")
    os.system("sudo k3s kubectl create -f generated.yaml")
    print("done")
    experiment.status = ExperimentStatus.RUNNING


def update_experiment_status(experiment: Experiment):
    if experiment.status == ExperimentStatus.COMPLETED or experiment.status == ExperimentStatus.STOPPED or experiment.status == ExperimentStatus.NOT_READY:
        return
    jobs = batch_v1.list_namespaced_job(experiment.created_by)

    job_list: dict[str, Container] = {}
    for node in experiment.nodes:
        if node.kubernetes_node.hostname == "":
            continue
        for container in node.containers:
            job_list[container.name] = container

    all_jobs_succeeded = True
    any_jobs_failed = False
    for job in jobs.items:
        # ignore smile apps, since the user can't track this
        if job.metadata.name.contains("smile-app"):
            continue
        if job.status.active:
            all_jobs_succeeded = False
            experiment.status = ExperimentStatus.RUNNING
            job_list[job.metadata.name].status = ContainerStatus.RUNNING
        if job.status.succeeded:
            job_list[job.metadata.name].status = ContainerStatus.SUCCEEDED
        if job.status.failed:
            job_list[job.metadata.name].status = ContainerStatus.FAILED
            any_jobs_failed = True
    if all_jobs_succeeded:
        experiment.status = ExperimentStatus.COMPLETED
        subprocess.Popen(f"sudo k3s kubectl delete namespace {experiment.created_by}", shell=True)
    if any_jobs_failed:
        experiment.status = ExperimentStatus.STOPPED
        subprocess.Popen(f"sudo k3s kubectl delete namespace {experiment.created_by}", shell=True)


def get_nodes():
    nodes = core_v1.list_node()
    node_list = []
    for node in nodes.items:
        node_list.append(Node(NodeType.UNASSIGNED, node.metadata.name))
    return node_list


def is_node_ready(hostname: str):
    status = core_v1.read_node_status(hostname)
    for condition in status.status.conditions:
        if condition.type == "Ready" and condition.status == "True":
            return True
    return False