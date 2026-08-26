"""Canonical API-to-runtime adapter for vNext execution."""

import inspect


class RuntimeAPIService:
    def __init__(self, runtime):
        self.runtime = runtime

    @staticmethod
    def _normalize(request):
        if not isinstance(request, dict):
            raise TypeError("request must be a mapping")
        goal = request.get("goal")
        task_id = request.get("task_id")
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal is required")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id is required")
        metadata = request.get("metadata")
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be a mapping")
        return goal, task_id, metadata

    async def execute(self, request):
        goal, task_id, metadata = self._normalize(request)
        result = self.runtime.execute(goal, task_id, metadata)
        if inspect.isawaitable(result):
            result = await result
        return {"task_id": task_id, "result": result}
