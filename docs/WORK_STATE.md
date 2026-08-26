# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** Scheduler worker cancellation now saves a resumable checkpoint; shutdown/cancellation regression added. Next step is full cancellation → restart validation and lifecycle hardening.

**Latest main:** `0fd58fe`

### Completed
- API → Runtime → Orchestrator → Scheduler → Execution regression coverage.
- Execution terminal results are persisted before response return.
- Duplicate execution is prevented by persisted terminal results.
- `CheckpointStore` is a facade over canonical `ExecutionStore`.
- Recovery skips tasks whose terminal result already exists.
- Scheduler checks persistence before enqueue and before execution.
- Real `ExecutionCoordinator` is exercised through Scheduler.
- Crash/restart/replay regression uses the real `CheckpointStore`.
- Cancellation/restart regression covers resumable checkpoint recovery.
- Scheduler worker cancellation now saves a checkpoint before propagating `CancelledError`.
- Worker always calls `queue.task_done()` in `finally`, preserving queue accounting.

### Exact next task
Run the complete cancellation → fresh Scheduler/Coordinator → recovery → terminal persistence → replay path against the current production checkpoint implementation. Then harden shutdown so cancelled workers can be restarted safely without stale worker references.

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
11. Cancelled worker references can be safely replaced on restart.

### Rule for the next agent
Inspect current `main` first. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
