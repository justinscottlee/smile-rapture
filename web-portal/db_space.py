from dataclasses import dataclass, field
from enum import Enum


class ExperimentStatus(Enum):
    NOT_READY = 0
    READY = 1
    RUNNING = 2
    STOPPED = 3
    COMPLETED = 4
    RESULTS_READY = 5


@dataclass
class Experiment:
    experiment_id: int
    status: int
    status_string: str
    reg_tag: str
    port_map: list[int]
    results: list[str] = field(default_factory=list)


@dataclass
class User:
    name_id: str
    email: str
    password: str
    experiments: list[Experiment]
