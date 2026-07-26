from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AgentProcessRequest(BaseModel):
    messages: List[str]
    context: Optional[Dict[str, Any]] = {}

class AgentProcessResponse(BaseModel):
    agent: str
    result: Dict[str, Any]
    messages: List[str]
