"""Tests for evidence, memory, routing and agent scoring."""

from aios_core.openhands import AgentScoreboard, AgentRole, TaskMemory, AgentMemoryEntry, TaskExtras, Gate, ReviewDecision
from aios_core.openhands.evidence import Evidence, EvidenceKind, dod_for_role
from aios_core.openhands.state_machine import OHStatus, can_transition, transition
from aios_core.orchestrator import TaskStatus


def test_review_repair_transition_returns_to_coder():
    extras = TaskExtras(task_id="t-1")
    assert can_transition(OHStatus.REVIEW, TaskStatus.RUNNING)
    assert transition(OHStatus.REVIEW, TaskStatus.RUNNING, extras) == TaskStatus.RUNNING
    assert Gate.REVIEW not in extras.passed_gates


def test_dod_requires_all_required_items():
    items = dod_for_role(AgentRole.CODER.value)
    assert items
    report = {item.key: True for item in items}
    assert all(report.values())


def test_memory_is_bounded_and_compact():
    memory = TaskMemory("t-1", max_entries=2)
    for i in range(3):
        memory.add(AgentMemoryEntry(role="coder", summary=f"step {i}"))
    assert len(memory.entries) == 2
    assert "step 2" in memory.compact_context()


def test_scoreboard_ranks_successful_agent_higher():
    board = AgentScoreboard()
    board.record("coder-a", success=True, iterations=1)
    board.record("coder-b", success=False, iterations=3, reviewer_rejected=True)
    assert board.rank(["coder-b", "coder-a"])[0] == "coder-a"


def test_evidence_model_is_machine_readable():
    evidence = Evidence(EvidenceKind.TEST, "pytest -q", "12 passed", True)
    assert evidence.passed
    assert evidence.kind == EvidenceKind.TEST
