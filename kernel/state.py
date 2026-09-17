from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Union, Literal
import sys
from functools import total_ordering

class RuntimeStatus(str, Enum):
    """Enumeration representing possible runtime states of the kernel.

    Attributes:
        CREATED: Kernel has been initialized but not started.
        STARTING: Kernel is in the process of starting.
        RUNNING: Kernel is fully operational.
        STOPPING: Kernel is in the process of stopping.
        STOPPED: Kernel has been stopped.
        FAILED: Kernel encountered an unrecoverable error.
    """
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"

@dataclass
class KernelState:
    """Data class representing the current state of the kernel.

    Attributes:
        status: Current runtime status of the kernel.
        agents: Number of active agents in the system.
        tasks: Number of active tasks in the system.
        version: Version string of the kernel.
    """
    status: RuntimeStatus = RuntimeStatus.CREATED
    agents: int = 0
    tasks: int = 0
    version: str = "0.1.0"

    def get_summary(self) -> Dict[str, Union[str, int]]:
        """Generates a summary dictionary of the kernel state.

        Returns:
            Dictionary containing:
            - status: Current runtime status
            - agents: Number of active agents
            - tasks: Number of active tasks
            - version: Kernel version
        """
        return {
            "status": self.status.value,
            "agents": self.agents,
            "tasks": self.tasks,
            "version": self.version
        }

def validate_kernel_state(state: KernelState) -> bool:
    """Validates the kernel state object.

    Args:
        state: KernelState object to validate

    Returns:
        True if state is valid, False otherwise

    Raises:
        TypeError: If any attribute has incorrect type
    """
    if not isinstance(state.status, RuntimeStatus):
        raise TypeError(f"status must be RuntimeStatus, got {type(state.status)}")
    if not isinstance(state.agents, int) or state.agents < 0:
        raise TypeError(f"agents must be non-negative int, got {type(state.agents)}")
    if not isinstance(state.tasks, int) or state.tasks < 0:
        raise TypeError(f"tasks must be non-negative int, got {type(state.tasks)}")
    if not isinstance(state.version, str) or not state.version:
        raise TypeError(f"version must be non-empty str, got {type(state.version)}")
    return True