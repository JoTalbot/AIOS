# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** real Scheduler → ExecutionCoordinator restart/replay boundary covered; ready for the next lifecycle integration batch.

**Latest main:** `46ec32f2ceadb665745f255fffe33986b60429bf`

### Completed
- API → Runtime → Orchestrator → Scheduler → Execution regression coverage.
- Execution terminal results are persisted before response return.
- Duplicate execution is prevented by persisted terminal results.
- `CheckpointStore` and `ExecutionStore` share the execution lifecycle.
- Recovery skips tasks whose terminal result already exists.
- Scheduler checks persistence before enqueue and again before execution.
- Real `ExecutionCoordinator` has been exercised through the Scheduler execution loop.
- Restart/replay regression proves the coordinator is invoked once and the second Scheduler does not enqueue the completed task.

### Exact next task
Add a genuine **crash-during-execution** test: persist a resumable checkpoint before simulated process termination, create a fresh Scheduler/ExecutionCoordinator, recover the task, continue execution, persist the terminal result, and verify replay does not execute again.

### Required invariants
1. Terminal result is persisted before response.
2. Restart never executes a task again when terminal result exists.
3. Stale checkpoint never overrides terminal state.
4. Checkpoint cleanup is idempotent.
5. Recovery and Scheduler share the same lifecycle state.
6. A recovered task executes exactly once after restart.
7. A completed task can be replayed without invoking the agent/tool again.
8. A crash before terminal persistence leaves a resumable checkpoint.

### Rule for the next agent
Inspect current `main` first. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
