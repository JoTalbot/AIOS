"""
AIOS Agent Runtime Core
Initial implementation layer for autonomous agent execution.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class AgentState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class AgentTask:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class AgentRuntime:
    """Minimal async runtime responsible for agent lifecycle and execution."""

    def __init__(self):
        self.state = AgentState.CREATED
        self.tasks: asyncio.Queue[AgentTask] = asyncio.Queue()
        self.results: Dict[str, Any] = {}
        self._worker: Optional[asyncio.Task] = None

    async def start(self):
        self.state = AgentState.RUNNING
        self._worker = asyncio.create_task(self._loop())

    async def stop(self):
        self.state = AgentState.STOPPED
        if self._worker:
            self._worker.cancel()

    async def submit(self, task: AgentTask):
        await self.tasks.put(task)
        return task.id

    async def _loop(self):
        while self.state == AgentState.RUNNING:
            task = await self.tasks.get()
            try:
                self.results[task.id] = await self.execute(task)
            except Exception as exc:
                self.state = AgentState.FAILED
                self.results[task.id] = {"error": str(exc)}

    async def execute(self, task: AgentTask):
        return {
            "task": task.name,
            "status": "completed",
            "payload": task.payload,
        }
