from datetime import datetime
from typing import List, Dict, Optional, Any

class EvolutionHistory:
    """A class to record and track the evolution history of a system or model.

    Attributes:
        entries (List[Dict[str, Any]]): A list of recorded entries, each containing
            version, result, and timestamp.
    """

    def __init__(self) -> None:
        """Initialize an empty EvolutionHistory instance."""
        self.entries: List[Dict[str, Any]] = []

    def record(self, version: str, result: Any) -> None:
        """Record a new entry in the evolution history.

        Args:
            version (str): The version identifier of the recorded entry.
            result (Any): The result associated with the version.
        """
        self.entries.append({
            "version": version,
            "result": result,
            "time": datetime.utcnow()
        })

    def latest(self) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent entry in the evolution history.

        Returns:
            Optional[Dict[str, Any]]: The latest entry if exists, otherwise None.
        """
        return self.entries[-1] if self.entries else None

    def get_summary(self) -> Dict[str, Any]:
        """Generate a summary of the evolution history.

        Returns:
            Dict[str, Any]: A summary containing the total number of entries,
                the latest version, and the latest result.
        """
        latest_entry = self.latest()
        return {
            "total_entries": len(self.entries),
            "latest_version": latest_entry["version"] if latest_entry else None,
            "latest_result": latest_entry["result"] if latest_entry else None,
        }