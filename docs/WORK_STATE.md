# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** fresh RuntimeContext recovery now has an integration regression covering persisted checkpoint → new context → recovery → execution → terminal persistence → replay protection.

**Latest main:** `f054b002514f7e25ff460090800bbce60d4e5369`

### Completed
- Canonical RuntimeContext → VNextOrchestrator → Scheduler → ExecutionCoordinator path.
- Terminal result persistence and replay protection.
- Checkpoint recovery idempotency per Scheduler.
- Factory-created cancellation → restart → recovery → persistence → replay coverage.
- Async RuntimeContext lifecycle and serialized restart/recovery.
- RuntimeContext invokes checkpoint restore through the canonical Scheduler.
- Concurrent execute/recover recovery race regression.
- PersistenceCheckpointStore uses the supplied canonical persistence object directly.
- Fresh-store checkpoint recovery regression.
- Fresh RuntimeContext persisted-checkpoint execution regression.

### Exact next task
Run the full integration suite against current `main`. Focus first on the fresh RuntimeContext test: validate the recovered task is actually consumed by the real Scheduler and ExecutionCoordinator, terminal state is persisted, checkpoint is deleted, and a subsequent submission with the same task id is a no-op.

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
17. Factory-created RuntimeContext is the integration path used by recovery tests.
18. Recovery restores each checkpointed task exactly once.
19. Restart does not duplicate workers or queue entries.
20. Concurrent RuntimeContext restarts are serialized.
21. Checkpoint recovery survives a fresh adapter/store instance.
22. Fresh RuntimeContext restart recovers from persisted state, not process-local memory.
23. Fresh RuntimeContext executes a recovered task exactly once and protects terminal replay.

### Rule for the next agent
Inspect current `main` first. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
