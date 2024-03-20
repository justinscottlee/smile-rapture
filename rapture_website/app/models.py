import typing
from dataclasses import dataclass, field, asdict
from enum import Enum
from uuid import UUID, uuid4
from collections.abc import Mapping
import time
import subprocess

from app.services.db import user_collection, experiment_collection
from app.services.kube import batch_v1, core_v1


class ExperimentStatus(Enum):
    NOT_READY = 0
    READY = 1
    RUNNING = 2
    STOPPED = 3
    COMPLETED = 4
    RESULTS_READY = 5


class ContainerStatus(Enum):
    PENDING = 0  # Kubernetes is trying to download the container image from the registry
    RUNNING = 1
    SUCCEEDED = 2
    FAILED = 3


class NodeType(Enum):
    UNASSIGNED = 0
    COMPUTE_PI = 1
    ROVER_PI = 2
    DRONE_PI = 3


@dataclass
class ResultEntry:
    data: str
    ts: float = field(default_factory=time.time)

    @classmethod
    def from_json(cls, doc: Mapping[str, typing.Any]) -> 'ResultEntry':
        return cls(data=str(doc.get('data')), ts=float(doc.get('ts')))

    def json(self):
        return asdict(self)


@dataclass
class User:
    name_id: str
    email: str
    password: str
    experiment_ids: list[UUID.hex] = field(default_factory=list)
    admin: bool = False
    created_at: float = field(default_factory=time.time)

    def json(self):
        return asdict(self)

    @classmethod
    def from_json(cls, doc: Mapping[str, typing.Any]) -> 'User':
        return cls(name_id=str(doc.get('name_id')), email=str(doc.get('email')), password=str(doc.get('password')),
                   experiment_ids=[str(exp_id) for exp_id in doc.get('experiment_ids')], admin=bool(doc.get('admin')),
                   created_at=float(doc.get('created_at')))

    @classmethod
    def get_by_id(cls, name_id: str) -> 'User' or None:
        user_data = user_collection.find_one({"name_id": name_id})

        if user_data:
            # Convert the MongoDB document to the User dataclass instance
            return cls.from_json(user_data)

        return None

    @classmethod
    def get_all(cls):
        return [cls.from_json(doc) for doc in user_collection.find({})]


@dataclass
class Container:
    src_dir: str  # user-uploaded source code directory
    python_requirements: str  # path to python requirements.txt
    registry_tag: str  # unique name for this container image
    ports: list[int]  # list of ports to open within kubernetes network for inter-container communication
    status: ContainerStatus
    name: str  # user-defined container name
    hostname: str = ""  # hostname of the node where this container is running
    stdout_log: list[str] = field(default_factory=list)  # stdout pipe

    @classmethod
    def from_json(cls, doc: Mapping[str, typing.Any]) -> 'Container':
        return cls(src_dir=str(doc.get('src_dir')), python_requirements=str(doc.get('python_requirements')),
                   registry_tag=str(doc.get("registry_tag")), ports=[int(port) for port in doc.get('ports', [])],
                   status=ContainerStatus(int(doc.get('status'))), name=str(doc.get('name')),
                   stdout_log=[str(entry) for entry in doc.get('stdout_log', [])])

    def json(self):
        container_dict = asdict(self)
        container_dict['status'] = self.status.value  # Convert Enum to its value
        return container_dict


@dataclass
class KubernetesNode:
    type: NodeType
    hostname: str

    def is_ready(self):
        status = core_v1.read_node_status(self.hostname)
        for condition in status.status.conditions:
            if condition.type == "Ready" and condition.status == "True":
                return True
        return False

    @classmethod
    def get_all(cls):
        nodes = core_v1.list_node()
        node_list = []
        for node in nodes.items:
            node_list.append(cls(type=NodeType.UNASSIGNED, hostname=node.metadata.name))
        return node_list


@dataclass
class Node:
    type: NodeType
    nickname: str = ""
    containers: list[Container] = field(default_factory=list)
    kubernetes_node: KubernetesNode = None

    @classmethod
    def from_json(cls, doc: Mapping[str, typing.Any]) -> 'Node':
        return cls(type=NodeType(int(doc.get('type'))),
                   containers=[Container.from_json(cont) for cont in doc.get('containers', [])])

    def json(self):
        node_dict = asdict(self)
        node_dict['type'] = int(self.type.value)  # Convert Enum to its value
        node_dict['containers'] = [cont.json() for cont in self.containers]
        return node_dict


@dataclass
class Experiment:
    experiment_uuid: UUID.hex = field(default_factory=(lambda: str(uuid4().hex)))
    nodes: list[Node] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.NOT_READY
    results: list[ResultEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    created_by: str = ""
    name: str = "none"

    def update(self):
        if self.status == ExperimentStatus.COMPLETED or self.status == ExperimentStatus.STOPPED or self.status == ExperimentStatus.NOT_READY:
            return
        jobs = batch_v1.list_namespaced_job(self.created_by)

        job_list: dict[str, Container] = {}
        for node in self.nodes:
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
                self.status = ExperimentStatus.RUNNING
                job_list[job.metadata.name].status = ContainerStatus.RUNNING
            if job.status.succeeded:
                job_list[job.metadata.name].status = ContainerStatus.SUCCEEDED
            if job.status.failed:
                job_list[job.metadata.name].status = ContainerStatus.FAILED
                any_jobs_failed = True
        if all_jobs_succeeded:
            self.status = ExperimentStatus.COMPLETED
            subprocess.Popen(f"sudo k3s kubectl delete namespace {self.created_by}", shell=True)
        if any_jobs_failed:
            self.status = ExperimentStatus.STOPPED
            subprocess.Popen(f"sudo k3s kubectl delete namespace {self.created_by}", shell=True)

    @classmethod
    def from_json(cls, doc: Mapping[str, typing.Any]) -> 'Experiment':
        return cls(
            experiment_uuid=str(doc.get('_id')),  # Now directly using the string _id
            nodes=[Node.from_json(node) for node in doc.get('nodes', [])],
            status=ExperimentStatus(int(doc.get('status'))),
            results=[ResultEntry(**result) for result in doc.get('results', [])],
            created_at=float(doc.get('created_at')),
            created_by=str(doc.get('created_by')),
            name=str(doc.get('name'))
        )

    def json(self):
        experiment_dict = asdict(self)

        # Use experiment_uuid as the document _id
        experiment_dict['_id'] = str(self.experiment_uuid)
        del experiment_dict['experiment_uuid']

        experiment_dict['status'] = self.status.value  # Convert Enum to its value

        # Convert nodes and results as before
        experiment_dict['nodes'] = [node.json() for node in self.nodes]
        experiment_dict['results'] = [result.json() for result in self.results]
        return experiment_dict

    @classmethod
    def get_by_id(cls, experiment_uuid: UUID.hex) -> 'Experiment' or None:
        exp_data = experiment_collection.find_one({"_id": experiment_uuid})

        if exp_data:
            # Convert the MongoDB document to the User dataclass instance
            return cls.from_json(exp_data)

        return None

    @classmethod
    def get_mul_by_id(cls, exp_ids: list[UUID.hex]) -> list['Experiment' or None]:
        return [cls.from_json(doc) for doc in experiment_collection.find({"_id": {"$in": exp_ids}})]

    @classmethod
    def get_all(cls):
        return [cls.from_json(doc) for doc in experiment_collection.find({})]
