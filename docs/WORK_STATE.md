# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** RuntimeContext now invokes the real checkpoint recovery object exactly once through the canonical Scheduler, and concurrent `execute()` / `recover()` calls are covered by regression.

**Latest main:** `43f22c0ec786d06ac154d575e4ce3268246b8a5e`

### Completed
- Canonical RuntimeContext → VNextOrchestrator → Scheduler → ExecutionCoordinator path.
- Terminal result persistence and replay protection.
- Checkpoint recovery idempotency per Scheduler.
- Factory-created cancellation → restart → recovery → persistence → replay coverage.
- Async RuntimeContext lifecycle and serialized restart.
- RuntimeContext now executes checkpoint `restore()` instead of merely marking recovery initialized.
- Concurrent execute/recover recovery race regression.

### Exact next task
Run the complete integration suite on current `main`. Then harden the canonical persistence/checkpoint adapter so restart recovery uses persisted checkpoints across a fresh process/store instance, not an in-memory `_items` cache.

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
17. Recovery restores each checkpointed task exactly once.
18. Restart does not duplicate workers or queue entries.
19. Concurrent RuntimeContext restarts are serialized.
20. Concurrent execute/recover calls initialize recovery exactly once.
21. Recovery works from persisted state after a fresh RuntimeContext/store instance.

### Rule for the next agent
Inspect current `main` first. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
