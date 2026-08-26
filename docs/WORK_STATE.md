# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** cancellation → real checkpoint → restart/recovery regression added; next step is to validate and harden the cancellation boundary.

**Latest main:** `14e8942`

### Completed
- API → Runtime → Orchestrator → Scheduler → Execution regression coverage.
- Execution terminal results are persisted before response return.
- Duplicate execution is prevented by persisted terminal results.
- `CheckpointStore` is a facade over canonical `ExecutionStore`.
- Recovery skips tasks whose terminal result already exists.
- Scheduler checks persistence before enqueue and before execution.
- Real `ExecutionCoordinator` is exercised through Scheduler.
- Crash/restart/replay regression uses the real `CheckpointStore`.
- Cancellation/restart regression now verifies cancellation leaves a resumable checkpoint and recovery completes the task without duplicate execution.

### Exact next task
Validate the cancellation regression against the actual Scheduler worker lifecycle and harden worker shutdown/cancellation semantics so queue accounting and checkpoint persistence remain correct under cancellation.

### Required invariants
1. Terminal result is persisted before response.
2. Restart never executes a task again when terminal result exists.
3. Stale checkpoint never overrides terminal state.
4. Checkpoint cleanup is idempotent.
5. Recovery and Scheduler share the same lifecycle state.
6. A recovered task executes exactly once after restart.
7. Completed replay does not invoke agent/tool again.
8. Cancellation before terminal persistence leaves a valid resumable checkpoint.
9. Production checkpoint path is tested.
10. Worker cancellation does not corrupt `Queue.join()` accounting.

### Rule for the next agent
Inspect current `main` first. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
