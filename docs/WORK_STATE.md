# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** KernelFactory now binds an available ExecutionCoordinator to the canonical RuntimePersistenceFacade before VNextOrchestrator wiring. Next step is the true RuntimeContext.execute() integration regression.

**Latest main:** `5398d53c73c4e76c2f4d605e3795aeb25f192c9a`

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
- RuntimePersistenceFacade exposes canonical result/state operations.
- KernelFactory binds an existing execution service to the canonical runtime persistence facade.

### Exact next task
Add/validate the true `KernelFactory → RuntimeContext.execute() → VNextOrchestrator → Scheduler → ExecutionCoordinator → canonical persistence` integration regression, including replay of the same task ID without a second coordinator execution.

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
14. Factory wiring preserves one canonical persistence/recovery path.
15. RuntimeContext.execute() reaches the real VNextOrchestrator and ExecutionCoordinator.
16. ExecutionCoordinator and Scheduler share the same canonical persistence object.

### Rule for the next agent
Inspect current `main` first. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
