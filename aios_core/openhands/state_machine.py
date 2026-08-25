"""State machine OpenHands-контура поверх канонического ``orchestrator.TaskStatus``.

Новые статусы контура объявлены здесь (StrEnum — значения совместимы по строке
с ``TaskStatus``); слияние в ``aios_core/orchestrator.py`` — фаза F6 плана
(protected-файл, правка вручную/владельцем + selfguard snapshot).
"""

from enum import StrEnum

from aios_core.orchestrator import TaskStatus

from .models import Gate, TaskExtras


class OHStatus(StrEnum):
    """Статусы контура, отсутствующие в каноническом ``TaskStatus`` до фазы F6."""

    READY = "ready"
    TESTING = "testing"
    REVIEW = "review"
    SECURITY_REVIEW = "security_review"
    QA = "qa"
    BLOCKED = "blocked"


# Допустимые переходы. Ключи/значения — str, чтобы принимать и TaskStatus, и OHStatus.
_TRANSITIONS: dict[str, frozenset[str]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.PLANNING, TaskStatus.CANCELLED}),
    TaskStatus.PLANNING: frozenset({OHStatus.READY, TaskStatus.FAILED, TaskStatus.CANCELLED}),
    OHStatus.READY: frozenset({TaskStatus.RUNNING, TaskStatus.CANCELLED}),
    TaskStatus.RUNNING: frozenset({OHStatus.TESTING, TaskStatus.FAILED, TaskStatus.CANCELLED}),
    OHStatus.TESTING: frozenset({OHStatus.REVIEW, TaskStatus.FAILED}),
    OHStatus.REVIEW: frozenset({OHStatus.SECURITY_REVIEW, OHStatus.BLOCKED}),
    OHStatus.SECURITY_REVIEW: frozenset({OHStatus.QA, OHStatus.BLOCKED}),
    OHStatus.QA: frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED}),
    OHStatus.BLOCKED: frozenset({TaskStatus.PLANNING, TaskStatus.CANCELLED}),
    TaskStatus.FAILED: frozenset({TaskStatus.PLANNING, TaskStatus.CANCELLED}),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}

# Какой гейт засчитывается при успешном прохождении стадии.
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
    """Множество статусов, в которые разрешён переход из ``status``."""
    return _TRANSITIONS.get(_s(status), frozenset())


def can_transition(src: TaskStatus | OHStatus | str, dst: TaskStatus | OHStatus | str) -> bool:
    """Допустим ли переход ``src → dst`` по таблице переходов."""
    return _s(dst) in allowed_transitions(src)


def transition(
    src: TaskStatus | OHStatus | str,
    dst: TaskStatus | OHStatus | str,
    extras: TaskExtras,
) -> str:
    """Проверить и применить переход ``src → dst`` с учётом gate-правил.

    Gate-правила:
    - успешный уход со стадии TESTING/REVIEW/SECURITY_REVIEW/QA засчитывает её гейт;
    - в COMPLETED нельзя, пока не пройдены все ``extras.required_gates``;
    - выход из FAILED/BLOCKED на повторную попытку возможен только при
      ``extras.can_retry()`` (лимит ``extras.max_retries``); при исчерпании
      лимита разрешён только CANCELLED.

    Возвращает целевой статус как ``str`` (сериализуемо и совместимо с обоими enum).
    """
    s_src, s_dst = _s(src), _s(dst)

    if not can_transition(s_src, s_dst):
        raise TransitionError(f"недопустимый переход: {s_src} -> {s_dst}")

    if s_src in (TaskStatus.FAILED, OHStatus.BLOCKED) and s_dst == TaskStatus.PLANNING:
        if not extras.can_retry():
            raise TransitionError(
                f"лимит попыток исчерпан ({extras.retry_count}/{extras.max_retries}); "
                "доступен только CANCELLED"
            )
        extras.register_retry()

    if s_dst == TaskStatus.COMPLETED and not extras.gates_satisfied():
        missing = ", ".join(sorted(g.value for g in extras.missing_gates()))
        raise TransitionError(f"COMPLETED запрещён: не пройдены гейты: {missing}")

    gate = _STAGE_GATE.get(s_src)
    if gate is not None and s_dst not in (TaskStatus.FAILED, OHStatus.BLOCKED):
        extras.passed_gates |= {gate}

    return s_dst
