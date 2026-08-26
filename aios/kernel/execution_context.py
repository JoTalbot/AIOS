"""AIOS v20 execution context.

Carries runtime metadata through the kernel execution pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ExecutionContext:
    """Context shared between kernel and runtime layers."""

    agent_id: str
    intent: str
    metadata: dict = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
