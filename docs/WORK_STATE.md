# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** RuntimeContext recovery ownership is wired and an integration regression now verifies idempotent recovery initialization.

**Latest main:** `808830a`

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
- Full worker lifecycle regression covers cancellation, restart, recovery, persistence and replay.
- KernelFactory wires scheduler + checkpoint store + recovery into RuntimeContext.
- RuntimeContext owns the canonical recovery entrypoint.
- Added RuntimeContext factory regression for idempotent recovery initialization.

### Exact next task
Extend the factory integration test with a real scheduler/persistence/executor path, then validate that `RuntimeContext.execute()` does not trigger duplicate recovery initialization or duplicate checkpoint restoration.

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
13. RuntimeContext recovery initialization is idempotent.
14. Factory wiring must preserve one canonical persistence/recovery path.

### Rule for the next agent
Inspect current `main` first. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
