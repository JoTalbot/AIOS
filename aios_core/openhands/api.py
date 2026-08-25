"""HTTP API OpenHands-контура (F8): FastAPI router поверх ``ContourService``.

Токен-авторизация как в octopus orchestrator: заголовок ``x-octopus-token``
(env ``OH_CONTOUR_TOKEN`` → ``OCTOPUS_TOKEN`` → ``"default"``). Router
self-contained: без явно переданного сервиса создаётся production-сервис
(Cloud-клиент по env, GitHub по env). Секреты в ответы не попадают.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .models import Gate, ReviewDecision
from .runner import RunResult
from .service import ContourService

TOKEN = os.getenv("OH_CONTOUR_TOKEN") or os.getenv("OCTOPUS_TOKEN", "default")

router = APIRouter(prefix="/api/v1/oh-contour", tags=["oh-contour"])

_service: ContourService | None = None


def _check_token(x_octopus_token: str = Header(default="")) -> None:
    if x_octopus_token != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _default_service() -> ContourService:
    """Production-сервис: Cloud-клиент и GitHub-helper по env."""
    from .client import OpenHandsClient
    from .github import GitHubHelper, GitRunner

    github = None
    gh_token = os.getenv("GITHUB_TOKEN", "")
    repo = os.getenv("OH_CONTOUR_REPO", "")
    if gh_token and repo:
        github = GitHubHelper(
            GitRunner(),
            repo=repo,
            token=gh_token,
            workspace=os.getenv("OH_CONTOUR_WORKSPACE", "."),
        )
    return ContourService(client=OpenHandsClient(), github=github, repository=repo or None)


def set_service(service: ContourService | None) -> None:
    """Подменить сервис (тесты / встраивание в host-приложение)."""
    global _service
    _service = service


def get_service() -> ContourService:
    """Текущий сервис; при первом обращении — production по env."""
    global _service
    if _service is None:
        _service = _default_service()
    return _service


class SubmitRequest(BaseModel):
    """Запрос на создание контурной задачи."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=50_000)
    branch: str = Field(default="", max_length=200)
    required_gates: list[str] | None = Field(default=None, description="tests/review/security_review/qa")
    max_retries: int = Field(default=3, ge=0, le=10)


class RunRequest(BaseModel):
    """Параметры запуска (пустые — запуск с текущими extras)."""



def _serialize_result(result: RunResult) -> dict:
    report = result.report
    return {
        "status": result.status,
        "pr_url": result.pr_url,
        "error": result.error,
        "retry_count": result.extras.retry_count,
        "passed_gates": sorted(g.value for g in result.extras.passed_gates),
        "review_decision": result.extras.review_decision.value if result.extras.review_decision else None,
        "failure_report": (
            {
                "reason": report.reason,
                "attempts": report.attempts,
                "last_error": report.last_error,
                "files_changed": list(report.files_changed),
                "suggested_next_step": report.suggested_next_step,
            }
            if report
            else None
        ),
    }


@router.post("/tasks", status_code=201)
def submit_task(req: SubmitRequest, x_octopus_token: str = Header(default="")):
    """Принять задачу в контур. Возвращает task_id."""
    _check_token(x_octopus_token)
    gates = None
    if req.required_gates is not None:
        try:
            gates = frozenset(Gate(g) for g in req.required_gates)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"unknown gate: {exc}") from exc
    task_id = get_service().submit(
        req.title,
        req.description,
        required_gates=gates,
        branch=req.branch,
        max_retries=req.max_retries,
    )
    return {"ok": True, "task_id": task_id}


@router.post("/tasks/{task_id}/run")
def run_task(task_id: str, x_octopus_token: str = Header(default="")):
    """Синхронно выполнить MVP-lifecycle задачи. Возвращает RunResult."""
    _check_token(x_octopus_token)
    try:
        result = get_service().run_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found") from None
    return {"ok": True, "result": _serialize_result(result)}


@router.get("/tasks/{task_id}")
def task_status(task_id: str, x_octopus_token: str = Header(default="")):
    """Сводный статус задачи (канонический + контурный)."""
    _check_token(x_octopus_token)
    try:
        return get_service().status(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found") from None


@router.get("/tasks/{task_id}/verdict")
def task_verdict(task_id: str, x_octopus_token: str = Header(default="")):
    """Вердикт последнего review (APPROVED/CHANGES_REQUESTED/null)."""
    _check_token(x_octopus_token)
    try:
        status = get_service().status(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found") from None
    decision = status.get("review_decision")
    return {
        "task_id": task_id,
        "review_decision": decision.value if isinstance(decision, ReviewDecision) else decision,
    }
