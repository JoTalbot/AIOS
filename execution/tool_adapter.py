"""Adapter between execution and the canonical tool registry."""

import inspect


class ExecutionToolAdapter:
    def __init__(self, registry=None):
        self.registry = registry

    async def execute(self, name, arguments=None, context=None):
        if self.registry is None:
            raise RuntimeError("tool registry is not configured")
        tool = self.registry.resolve(name) if hasattr(self.registry, "resolve") else None
        if tool is None:
            raise KeyError(f"unknown tool: {name}")
        payload = arguments or {}
        if hasattr(tool, "execute"):
            value = tool.execute(payload, context=context)
        elif callable(tool):
            value = tool(payload, context=context)
        else:
            raise TypeError(f"tool {name!r} is not executable")
        return await value if inspect.isawaitable(value) else value
