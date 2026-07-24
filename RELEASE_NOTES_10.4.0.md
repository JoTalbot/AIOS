# AIOS v10.4.0 Release Notes

**Date**: 2026-07-24  
**Version**: 10.4.0  
**Tests**: 1882 passed, 0 failures (+212 new)  

## New Modules

### 1. Feature Flags System (`feature_flags.py`)
Complete feature flag system with rollout strategies, targeting rules, variants, dependencies, lifecycle, metrics, and audit logging.

**Features**:
- **Flag lifecycle**: Draft → Staging → Production → Archived states
- **Rollout strategies**: Percentage-based, User list, Scheduled time-based, Targeting rules
- **Targeting rules**: 7 operators (eq, neq, in, not_in, gte, lte, contains) for attribute-based conditions
- **Flag variants**: A/B testing support with deterministic hash-based variant selection
- **Parent dependencies**: Child flags require parent flag to be enabled
- **Metrics tracking**: Evaluation count, exposure count, exposure rate per flag
- **Audit logging**: All flag changes recorded (enable, disable, toggle, update, register, archive)
- **Deterministic hashing**: SHA256-based hash for consistent user experience across percentage rollouts
- **Backward-compatible façade**: `FeatureFlags` class preserves original enable/disable/is_enabled/toggle/list API

### 2. RBAC System (`rbac.py`)
Full Role-Based Access Control with hierarchy, resource-based permissions, policies, constraints, and audit trail.

**Features**:
- **Permissions**: Resource:action format (e.g., "listing:read") with wildcard support (*:*, resource:*, action:*)
- **Permission sets**: Named groups of permissions for easy bulk assignment
- **Role hierarchy**: Parent/child role inheritance with depth-bounded resolution (max 10 levels)
- **Access policies**: Conditional rules — time-of-day restrictions, IP range (CIDR) filtering, platform gating, custom attributes
- **User assignment**: Role assignments with expiry times, revocation, active/expired status tracking
- **Constraints**: Mutually exclusive roles (buyer ↔ seller), max roles per user limit
- **Audit trail**: All access decisions logged (granted/denied) with reason tracking
- **Frozen permissions**: Immutable Permission dataclass preventing accidental mutation
- **Backward-compatible façade**: `RBAC` class preserves original create_role/has_permission/check_access/stats API

### 3. Workflow Engine (`workflow.py`)
DAG-based workflow execution with parallel steps, condition gates, retry policies, compensation actions, and templates.

**Features**:
- **DAG execution**: Topological sort → layered parallel execution → result passing between steps
- **Retry policies**: Constant, linear, exponential backoff with configurable max retries, retryable exceptions, max delay cap
- **Timeout policies**: Per-step timeout with grace period
- **Condition gates**: If/else branching — condition_fn evaluated against workflow context + step results
- **Compensation actions (Saga pattern)**: On failure, all successful step compensations run in reverse order
- **Result passing**: Dependency results injected as `{step_id}_result` kwargs into dependent steps
- **Workflow templates**: Reusable blueprints with step definitions → instantiate workflows with action maps
- **Detailed execution trace**: WorkflowResult with per-step status, duration, errors, compensation results
- **Backward-compatible façade**: `WorkflowEngine` class preserves original create_workflow/add_step/execute/stats API

## Bug Fixes
- **Workflow condition gates**: Now receive combined workflow context + step context (was only step context before)
- **Workflow compensation (Saga)**: Failed workflow now compensates ALL previously successful steps in reverse order, not just the failed step

## Module Enhancement
- `feature_flags.py`: 34-line stub → 360-line full implementation (10x growth)
- `rbac.py`: 34-line stub → 470-line full implementation (14x growth)
- `workflow.py`: 74-line stub → 560-line full implementation (7.5x growth)

## Test Coverage
- **212 new tests** across 12 test classes:
  - TestFeatureFlagStore: 35 tests (registration, mutations, evaluation, rollout, targeting, variants, metrics, audit, queries)
  - TestFeatureFlagsFacade: 7 tests (backward-compatible API)
  - TestFeatureFlagsGlobal: 1 test (singleton)
  - TestPermission: 8 tests (str, from_string, matches, wildcard, frozen)
  - TestPermissionSet: 4 tests (add, contains, wildcard, remove)
  - TestRole: 5 tests (add/remove permission, parent management)
  - TestRoleHierarchy: 7 tests (resolve, inheritance, circular safety, max depth)
  - TestRBACEngine: 25 tests (roles, permission sets, assignments, access checks, policies, constraints, audit, stats)
  - TestRBACFacade: 5 tests (backward-compatible API)
  - TestRBACGlobal: 1 test (singleton)
  - TestWorkflowEngine: 18 tests (create, add step, execute, retry, templates, query, stats, cancel)
  - TestWorkflowEdgeCases: 9 tests (empty, no action, durations, context, result passing, retry exceptions, compensation order)

## Integration Tests
- 3 cross-module integration tests: Feature flags + RBAC access control, Workflow + feature flag condition gates, RBAC role hierarchy + flag state

## Previous Versions
- v10.3.0: Agent Memory System, Platform Health Monitor, Export/Import Pipeline (54 tests)
- v10.2.0: Credential Manager, Price Alert System, Scraping Strategy Templates (58 tests)
- v10.1.0: AB Testing Engine, Knowledge Graph, Auto-Tuning (44 tests)
- v10.0.0: Price Prediction ML, Image Comparison, Fleet Scheduler (110 tests)
