"""State machine OpenHands-контура с gate-aware переходами."""

from enum import StrEnum

from aios_core.orchestrator import TaskStatus
from .models import Gate, TaskExtras


class OHStatus(StrEnum):
    READY = "ready"
    TESTING = "testing"
    REVIEW = "review"
    SECURITY_REVIEW = "security_review"
    QA = "qa"
    BLOCKED = "blocked"


_TRANSITIONS: dict[str, frozenset[str]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.PLANNING, TaskStatus.CANCELLED}),
    TaskStatus.PLANNING: frozenset({OHStatus.READY, TaskStatus.FAILED, TaskStatus.CANCELLED}),
    OHStatus.READY: frozenset({TaskStatus.RUNNING, TaskStatus.CANCELLED}),
    TaskStatus.RUNNING: frozenset({OHStatus.TESTING, TaskStatus.FAILED, TaskStatus.CANCELLED}),
    OHStatus.TESTING: frozenset({OHStatus.REVIEW, TaskStatus.FAILED, OHStatus.BLOCKED}),
    OHStatus.REVIEW: frozenset({OHStatus.SECURITY_REVIEW, OHStatus.QA, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.RUNNING, OHStatus.BLOCKED}),
    OHStatus.SECURITY_REVIEW: frozenset({OHStatus.QA, TaskStatus.COMPLETED, TaskStatus.FAILED, OHStatus.BLOCKED}),
    OHStatus.QA: frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED, OHStatus.BLOCKED}),
    OHStatus.BLOCKED: frozenset({TaskStatus.PLANNING, TaskStatus.CANCELLED}),
    TaskStatus.FAILED: frozenset({TaskStatus.PLANNING, TaskStatus.CANCELLED}),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}

_STAGE_GATE: dict[str, Gate] = {
    OHStatus.TESTING: Gate.TESTS,
    OHStatus.REVIEW: Gate.REVIEW,
    OHStatus.SECURITY_REVIEW: Gate.SECURITY_REVIEW,
    OHStatus.QA: Gate.QA,
}


class TransitionError(ValueError):
    """Недопустимый переход или нарушение gate-правила."""


def _s(status: TaskStatus | OHStatus | str) -> str:
    return str(status.value if isinstance(status, StrEnum) else status)


def allowed_transitions(status: TaskStatus | OHStatus | str) -> frozenset[str]:
    return _TRANSITIONS.get(_s(status), frozenset())


def can_transition(src: TaskStatus | OHStatus | str, dst: TaskStatus | OHStatus | str) -> bool:
    return _s(dst) in allowed_transitions(src)


def transition(src: TaskStatus | OHStatus | str, dst: TaskStatus | OHStatus | str, extras: TaskExtras) -> str:
    s_src, s_dst = _s(src), _s(dst)
    if not can_transition(s_src, s_dst):
        raise TransitionError(f"недопустимый переход: {s_src} -> {s_dst}")

    if s_src in (TaskStatus.FAILED, OHStatus.BLOCKED) and s_dst == TaskStatus.PLANNING:
        if not extras.can_retry():
            raise TransitionError(
                f"лимит попыток исчерпан ({extras.retry_count}/{extras.max_retries}); доступен только CANCELLED"
            )
        extras.register_retry()

    # Reviewer -> Coder repair не является прохождением REVIEW gate.
    # Gate считается пройденным только при переходе дальше по pipeline.
    is_repair = s_src == OHStatus.REVIEW and s_dst == TaskStatus.RUNNING
    gate = _STAGE_GATE.get(s_src)
    if gate is not None and not is_repair and s_dst not in (
        TaskStatus.FAILED,
        OHStatus.BLOCKED,
        TaskStatus.CANCELLED,
    ):
        extras.passed_gates = frozenset((*extras.passed_gates, gate))

    if s_dst == TaskStatus.COMPLETED and not extras.gates_satisfied():
        missing = ", ".join(sorted(g.value for g in extras.missing_gates()))
        raise TransitionError(f"COMPLETED запрещён: не пройдены гейты: {missing}")
    return s_dst
