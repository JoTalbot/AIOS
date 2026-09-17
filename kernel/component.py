from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class KernelComponent(ABC):
    """Abstract base class for AIOS kernel-managed components.

    This class defines the contract for all components managed by the AIOS kernel,
    including initialization, lifecycle management, and health monitoring.

    Attributes:
        name (Optional[str]): Unique identifier of the component. Defaults to None.
        requires (List[str]): List of component names this component depends on. Defaults to empty list.
    """

    name: Optional[str] = None
    requires: List[str] = []

    def initialize(self) -> None:
        """Initialize the component and its dependencies.

        Performs one-time setup operations required before the component can be started.
        """
        pass

    def start(self) -> None:
        """Start the component and its dependencies.

        Activates the component's main functionality after initialization.
        """
        pass

    def stop(self) -> None:
        """Stop the component and release allocated resources.

        Gracefully shuts down the component and cleans up any allocated resources.
        """
        pass

    def health(self) -> bool:
        """Check the component's health status.

        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        return True

    def get_summary(self) -> Dict[str, Any]:
        """Generate a summary of the component's state and metadata.

        Returns:
            Dict[str, Any]: Dictionary containing component metadata including:
                - name: Component identifier
                - requires: List of dependencies
                - status: Current status (initialized/started/stopped)
                - health: Health status
        """
        status = "initialized"
        if hasattr(self, '_started') and self._started:
            status = "started"
        elif hasattr(self, '_stopped') and self._stopped:
            status = "stopped"

        return {
            "name": self.name,
            "requires": self.requires,
            "status": status,
            "health": self.health()
        }