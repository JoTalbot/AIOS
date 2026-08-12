"""Лёгкий HTTP-узел AIOS для Fly.io и P2P-обмена.

Модуль намеренно не загружает тяжёлые компоненты AIOS при старте. Это позволяет
запускать демонстрационный узел на небольшой Fly Machine и импортировать LLM-рой
только по запросу к соответствующему endpoint.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket

from fastapi import FastAPI, HTTPException

from aios_core import __version__ as AIOS_VERSION
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AIOS P2P Node",
    version=AIOS_VERSION,
    description="Облегчённый демонстрационный API AIOS для Fly.io.",
)


class NodeInfo(BaseModel):
    """Публичная информация о текущем узле AIOS."""

    hostname: str
    ip: str
    status: str
    capabilities: list[str]


class DebateRequest(BaseModel):
    """Запрос на запуск многоагентного обсуждения."""

    topic: str = Field(min_length=1, max_length=4_000)


class DebateResponse(BaseModel):
    """Итог многоагентного обсуждения."""

    status: str
    mode: str
    result: str


def _node_ip() -> str:
    """Возвращает адрес контейнера, не ломая discovery при ошибке DNS."""

    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


@app.get("/", tags=["System"])
async def root() -> dict[str, object]:
    """Краткая информация и ссылки на основные точки входа."""

    return {
        "service": "AIOS P2P Node",
        "status": "online",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
        "discovery": "/api/p2p/discover",
    }


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    """Быстрая проверка для Fly Proxy без внешних зависимостей."""

    return {"status": "healthy", "service": "aios-p2p"}


@app.get("/api/p2p/discover", response_model=NodeInfo, tags=["P2P"])
def discover_node() -> NodeInfo:
    """Публикует состояние и возможности узла."""

    return NodeInfo(
        hostname=socket.gethostname(),
        ip=_node_ip(),
        status="ACTIVE",
        capabilities=["llm_debate", "ast_refactor", "browser_vision"],
    )


@app.post("/api/p2p/task", tags=["P2P"])
def receive_task(task_name: str) -> dict[str, str]:
    """Принимает имя задачи, сохраняя совместимость с прежним API."""

    return {
        "status": "accepted",
        "task": task_name,
        "message": "Task queued for the swarm.",
    }


@app.post("/api/swarm/debate", response_model=DebateResponse, tags=["Swarm"])
async def run_swarm_debate(request: DebateRequest) -> DebateResponse:
    """Запускает LLM-рой без блокировки event loop FastAPI.

    При отсутствии ``OPENROUTER_API_KEY`` встроенный контроллер возвращает
    демонстрационный mock-ответ. Тяжёлые модули импортируются лениво, чтобы
    health check оставался доступен даже при недоступности LLM-провайдера.
    """

    try:
        from aios_core.llm_swarm_debate import LLMSwarm

        result = await asyncio.wait_for(
            asyncio.to_thread(LLMSwarm().start_debate, request.topic),
            timeout=120,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="LLM swarm timed out") from exc
    except Exception as exc:
        logger.exception("LLM swarm request failed")
        raise HTTPException(status_code=502, detail="LLM swarm request failed") from exc

    mode = "openrouter" if os.getenv("OPENROUTER_API_KEY") else "mock"
    return DebateResponse(status="completed", mode=mode, result=result)
