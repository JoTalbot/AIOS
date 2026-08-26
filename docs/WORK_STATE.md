# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** Scheduler worker lifecycle hardened for cancellation/restart; cancelled worker references are removed and fresh workers can be started safely.

**Latest main:** `813ddd7`

### Completed
- API → Runtime → Orchestrator → Scheduler → Execution regression coverage.
- Terminal execution results persist before response.
- Duplicate execution is prevented by persisted terminal results.
- CheckpointStore is a facade over canonical ExecutionStore.
- Recovery skips tasks whose terminal result already exists.
- Scheduler checks persistence before enqueue and before execution.
- Real ExecutionCoordinator is exercised through Scheduler.
- Crash/restart/replay regression uses the real CheckpointStore.
- Cancellation/restart regression covers resumable checkpoint recovery.
- Worker cancellation saves a checkpoint and preserves queue accounting.
- `Scheduler.start()` removes completed/cancelled worker references before creating replacements.
- `Scheduler.stop()` clears worker references before cancellation/gather.

### Exact next task
Run a full worker lifecycle regression: cancel a worker during execution, restart workers on the same Scheduler, recover the checkpoint, complete the task, and verify a later replay does not execute again.

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

### Rule for the next agent
Inspect current `main` first. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
