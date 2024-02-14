import typing
from dataclasses import dataclass, field, asdict
from enum import Enum
from uuid import UUID, uuid4
from collections.abc import Mapping
import time


def uuid4_hex() -> UUID.hex:
    # Return the hexadecimal representation of UUID
    return uuid4().hex


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
    NODE_AMD64 = 0
    NODE_ARM64 = 1
    DRONE_ARM64 = 2


@dataclass
class ResultEntry:
    data: str
    ts: float = field(default_factory=time.time)

    @classmethod
    def from_json(cls, doc: Mapping[str, typing.Any]) -> 'ResultEntry':
        return cls(data=str(doc['data']), ts=float(doc['ts']))

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

    @classmethod
    def from_json(cls, doc: Mapping[str, typing.Any]) -> 'User':
        return cls(name_id=str(doc['name_id']), email=str(doc['email']), password=str(doc['password']),
                   experiment_ids=[str(exp_id) for exp_id in doc['experiment_ids']], admin=bool(doc['admin']),
                   created_at=float(doc['created_at']))

    def json(self):
        return asdict(self)


@dataclass
class Container:
    src_dir: str  # user-uploaded source code directory
    python_requirements: str  # path to python requirements.txt
    registry_tag: str  # unique name for this container image
    ports: list[int]  # list of ports to open within kubernetes network for inter-container communication
    status: ContainerStatus
    name: str  # user-defined container name

    @classmethod
    def from_json(cls, doc: Mapping[str, typing.Any]) -> 'Container':
        return cls(src_dir=str(doc['src_dir']), python_requirements=str(doc['python_requirements']),
                   registry_tag=str(doc['registry_tag']), ports=[int(port) for port in doc['ports']],
                   status=ContainerStatus(int(doc['status'])), name=str(doc['name']))

    def json(self):
        container_dict = asdict(self)
        container_dict['status'] = self.status.value  # Convert Enum to its value
        return container_dict


@dataclass
class Node:
    type: NodeType
    containers: list[Container] = field(default_factory=list)

    @classmethod
    def from_json(cls, doc: Mapping[str, typing.Any]) -> 'Node':
        return cls(type=NodeType(int(doc['type'])),
                   containers=[Container.from_json(cont) for cont in doc['containers']])

    def json(self):
        node_dict = asdict(self)
        node_dict['type'] = int(self.type.value)  # Convert Enum to its value
        node_dict['containers'] = [cont.json() for cont in self.containers]
        return node_dict


@dataclass
class Experiment:
    experiment_uuid: UUID.hex = field(default_factory=uuid4_hex)
    nodes: list[Node] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.NOT_READY
    results: list[ResultEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    created_by: str = ""
    name: str = "none"

    @classmethod
    def from_json(cls, doc: Mapping[str, typing.Any]) -> 'Experiment':
        return cls(
            experiment_uuid=str(doc['_id']),  # Now directly using the string _id
            nodes=[Node.from_json(node) for node in doc['nodes']],
            status=ExperimentStatus(int(doc['status'])),
            results=[ResultEntry(**result) for result in doc['results']],
            created_at=float(doc['created_at']),
            created_by=str(doc['created_by']),
            name=str(doc['name'])
        )

    def json(self):
        experiment_dict = asdict(self)

        experiment_dict['_id'] = self.experiment_uuid  # Use experiment_uuid as the document _id
        experiment_dict['status'] = self.status.value  # Convert Enum to its value

        # Convert nodes and results as before
        experiment_dict['nodes'] = [node.json() for node in self.nodes]
        experiment_dict['results'] = [result.json() for result in self.results]
        return experiment_dict
