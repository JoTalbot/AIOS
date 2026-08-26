# AIOS v5 Migration PR Roadmap

## PR Sequence

- PR #1 Core Foundation
- PR #2 ExecutionKernel
- PR #3 EventBus and Observability
- PR #4 Orchestrator Migration
- PR #5 Memory Graph and Recovery
- PR #6 Skill Engine
- PR #7 Multi-Agent Scheduler
- PR #8 Distributed Runtime
- PR #9 Security Governance
- PR #10 Production Hardening

## Release Flow

feature branches -> release/v5.0-rc1 -> release/v5.0 -> main

## Rules

- Execution through ExecutionKernel only
- Events for state changes
- Recoverable agent state
- Plugin-based extensions
- Auditable autonomous actions
