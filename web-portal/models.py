from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
import bcrypt
import time


class ExperimentStatus(Enum):
    NOT_READY = 0
    READY = 1
    RUNNING = 2
    STOPPED = 3
    COMPLETED = 4
    RESULTS_READY = 5

class ContainerStatus(Enum):
    PENDING = 0 # Kubernetes is trying to download the container image from the registry
    RUNNING = 1
    SUCCEEDED = 2
    FAILED = 3

class NodeType(Enum):
    DRONE_ARM64 = 0
    NODE_ARM64 = 1
    NODE_AMD64 = 2

@dataclass
class ResultEntry:
    data: str
    ts: float = field(default_factory=time.time)


@dataclass
class User:
    name_id: str
    email: str
    password: str
    experiment_ids: list[UUID.hex] = field(default_factory=list)
    admin: bool = False

@dataclass
class Container:
    src_dir: str # user-uploaded source code directory
    python_requirements: str # path to python requirements.txt
    registry_tag: str # unique name for this container image
    ports: list[int] # list of ports to open within kubernetes network for inter-container communication
    status: ContainerStatus

@dataclass
class Node:
    type: NodeType
    containers: list[Container] = field(default_factory=list)

@dataclass
class Experiment:
    experiment_uuid: str
    nodes: list[Node] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.NOT_READY
    results: list[ResultEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    created_by: str = "none"