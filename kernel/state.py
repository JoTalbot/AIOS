from dataclasses import dataclass
from enum import Enum


class RuntimeStatus(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class KernelState:
    status: RuntimeStatus = RuntimeStatus.CREATED
    agents: int = 0
    tasks: int = 0
    version: str = "0.1.0"
