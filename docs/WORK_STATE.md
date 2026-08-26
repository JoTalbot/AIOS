# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** canonical crash/restart test now uses the real `CheckpointStore` backed by `ExecutionStore`; ready for crash/cancellation hardening.

**Latest main:** `1bac0c0`

### Completed
- API → Runtime → Orchestrator → Scheduler → Execution regression coverage.
- Execution terminal results are persisted before response return.
- Duplicate execution is prevented by persisted terminal results.
- `CheckpointStore` is a compatibility facade over canonical `ExecutionStore`.
- Recovery skips tasks whose terminal result already exists.
- Scheduler checks persistence before enqueue and before execution.
- Real `ExecutionCoordinator` is exercised through the Scheduler execution loop.
- Restart/replay regression proves completed tasks are not executed twice.
- Crash/restart/replay regression now uses the repository's actual `CheckpointStore` and `ExecutionStore`, not a mock checkpoint store.

### Exact next task
Harden cancellation/crash boundaries: prove a cancellation during execution leaves a valid resumable checkpoint, then restart a fresh Scheduler/Coordinator and complete the task without duplicate execution.

### Required invariants
1. Terminal result is persisted before response.
2. Restart never executes a task again when terminal result exists.
3. Stale checkpoint never overrides terminal state.
4. Checkpoint cleanup is idempotent.
5. Recovery and Scheduler share the same lifecycle state.
6. A recovered task executes exactly once after restart.
7. A completed task can be replayed without invoking the agent/tool again.
8. A crash/cancellation before terminal persistence leaves a valid resumable checkpoint.
9. The production checkpoint path is tested; mocks do not replace it.

### Rule for the next agent
Inspect current `main` first. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
