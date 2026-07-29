from typing import Any

from pydantic import BaseModel


class AgentProcessRequest(BaseModel):
    messages: list[str]
    context: dict[str, Any] | None = {}


class AgentProcessResponse(BaseModel):
    agent: str
    result: dict[str, Any]
    messages: list[str]
