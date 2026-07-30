"""
P2P Decentralization Module (Vector 5)
Обеспечивает меж-узловое общение (Swarm Node Discovery).
"""
from fastapi import FastAPI
from pydantic import BaseModel
import socket

app = FastAPI(title="AIOS P2P Node")

class NodeInfo(BaseModel):
    hostname: str
    ip: str
    status: str
    capabilities: list

@app.get("/api/p2p/discover", response_model=NodeInfo)
def discover_node():
    return NodeInfo(
        hostname=socket.gethostname(),
        ip=socket.gethostbyname(socket.gethostname()),
        status="ACTIVE",
        capabilities=["llm_debate", "ast_refactor", "browser_vision"]
    )

@app.post("/api/p2p/task")
def receive_task(task_name: str):
    return {"status": "accepted", "task": task_name, "message": "Task queued for the swarm."}

# Запуск: uvicorn aios_core.p2p_network:app --host 0.0.0.0 --port 8001
