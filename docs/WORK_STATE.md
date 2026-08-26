# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** crash-during-execution checkpoint/restart/replay regression added; ready to validate and then harden the recovery lifecycle.

**Latest main:** `81eb2eb0b79a56de9d3074fcf01963e848915cb1`

### Completed
- API → Runtime → Orchestrator → Scheduler → Execution regression coverage.
- Execution terminal results are persisted before response return.
- Duplicate execution is prevented by persisted terminal results.
- `CheckpointStore` and `ExecutionStore` share the execution lifecycle.
- Recovery skips tasks whose terminal result already exists.
- Scheduler checks persistence before enqueue and again before execution.
- Real `ExecutionCoordinator` has been exercised through the Scheduler execution loop.
- Restart/replay regression proves completed tasks are not executed twice.
- Added crash-once runner regression: first execution fails before terminal persistence, checkpoint remains, recovery resumes on a fresh Scheduler, terminal result is persisted, checkpoint is removed, and later replay does not execute again.

### Exact next task
Validate the crash/restart regression against the repository's actual checkpoint implementation and then harden checkpoint persistence so cancellation/crash boundaries cannot lose resumable state.

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
