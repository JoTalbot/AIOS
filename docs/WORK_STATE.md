# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** full worker cancellation → restart → recovery → persistence → replay regression added.

**Latest main:** `2d0a0cd`

### Completed
- API → Runtime → Orchestrator → Scheduler → Execution regression coverage.
- Terminal execution results persist before response.
- Duplicate execution is prevented by persisted terminal results.
- CheckpointStore is a facade over canonical ExecutionStore.
- Recovery skips tasks whose terminal result already exists.
- Scheduler checks persistence before enqueue and before execution.
- Real ExecutionCoordinator is exercised through Scheduler.
- Crash/restart/replay regression uses the real CheckpointStore.
- Cancellation saves a resumable checkpoint and preserves queue accounting.
- Cancelled worker references can be safely replaced on restart.
- Full worker lifecycle regression covers cancellation, worker restart, checkpoint recovery, terminal persistence and replay without duplicate execution.

### Exact next task
Validate the new worker lifecycle test against the current production execution path. Then move the recovery lifecycle from test-oriented orchestration into the canonical RuntimeContext lifecycle, ensuring restart/recovery is initialized once and owns Scheduler + persistence consistently.

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
10. Worker cancellation does not corrupt Queue.join() accounting.
11. Cancelled worker references can be safely replaced on restart.
12. RuntimeContext owns the canonical restart/recovery lifecycle.

### Rule for the next agent
Inspect current `main` first. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
