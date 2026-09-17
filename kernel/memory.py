from collections import deque
from typing import Any, List, Optional, Union

class MemoryOS:
    """AIOS memory layer: short term and long term storage interface.

    Attributes:
        short_memory: Deque for short-term memory with fixed max length.
        long_memory: List for long-term memory storage.
    """

    def __init__(self, max_short: int = 100) -> None:
        """Initialize MemoryOS with specified short-term memory capacity.

        Args:
            max_short: Maximum number of items in short-term memory (default: 100).
        """
        self.short_memory: deque[Any] = deque(maxlen=max_short)
        self.long_memory: list[Any] = []

    def remember(self, item: Any, permanent: bool = False) -> None:
        """Store an item in memory.

        Args:
            item: The item to remember.
            permanent: If True, store in long-term memory (default: False).
        """
        self.short_memory.append(item)
        if permanent:
            self.long_memory.append(item)

    def recall(self, query: Optional[str] = None) -> Union[List[Any], List[str]]:
        """Retrieve items from memory based on query.

        Args:
            query: Optional search string. If None, returns all short-term memory.
                  Case-insensitive substring matching is used for long-term memory.

        Returns:
            List of matching items or all short-term memory items.
        """
        if query is None:
            return list(self.short_memory)

        return [
            item for item in self.long_memory
            if query.lower() in str(item).lower()
        ]

    def get_summary(self) -> dict[str, Any]:
        """Generate a summary of current memory state.

        Returns:
            Dictionary containing:
            - short_memory_size: Current size of short-term memory
            - long_memory_size: Current size of long-term memory
            - short_memory_sample: First 3 items from short-term memory (or all if <3)
            - long_memory_sample: First 3 items from long-term memory (or all if <3)
        """
        return {
            "short_memory_size": len(self.short_memory),
            "long_memory_size": len(self.long_memory),
            "short_memory_sample": list(self.short_memory)[:3],
            "long_memory_sample": self.long_memory[:3]
        }