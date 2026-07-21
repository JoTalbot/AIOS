# AIOS Architecture Documentation

> **AIOS (AI Operating System)** — Self-Evolving Distributed Operating System for Application Intelligence
> **Version:** 9.0.0-alpha.14 | **Runtime:** Octopus Runtime | **Constitution:** 67 Articles, 1,320 Rules

---

## Table of Contents

1. [Overview](#overview)
2. [Constitutional Governance](#constitutional-governance)
3. [Core Subsystems](#core-subsystems)
4. [Execution Pipeline](#execution-pipeline)
5. [API Layers](#api-layers)
6. [Persistence Layer](#persistence-layer)
7. [Testing & Self-Validation](#testing--self-validation)
8. [Evolution Pipeline](#evolution-pipeline)
9. [Security Model](#security-model)
10. [Quick Reference](#quick-reference)

---

## Overview

AIOS is a **self-evolving distributed operating system** designed for application intelligence with built-in constitutional governance. Every action, from memory storage to system evolution, passes through a **7-phase constitutional evaluation pipeline** before execution.

### Key Principles

| Principle | Description |
|-----------|-------------|
| **Limited Autonomy** | Every action requires goal, scope, risk assessment, and audit logging |
| **Constitutional Supremacy** | 67 immutable articles govern all system behavior |
| **Memory Separation** | Three categories: Personal (never federated), Operational, Constitutional (immutable) |
| **Controlled Evolution** | 7-stage pipeline with human approval gates |
| **Explainable Decisions** | Full reasoning chains with confidence scores |
| **Continuous Learning** | Experience recording → Pattern extraction → Recommendations |

### System Statistics

- **Constitution:** 67 articles, 1,320 rules (860 MUST, 93 MUST NOT, 227 SHOULD, 139 MAY)
- **Policies:** 3 YAML policies (Security, Evolution, Federation)
- **Test Coverage:** 438 tests passing (4 built-in suites, 23 test cases)
- **API Endpoints:** 30+ REST + JSON-RPC 2.0 MCP Gateway

---

## Constitutional Governance

### Article Structure

Each constitutional article follows this format:
```markdown
# Article N — Title
**Status:** Immutable Core Law | **Level:** Constitutional | **Scope:** All AIOS entities

# Section N.M — Section Title
**MUST** / **MUST NOT** / **SHOULD** / **MAY** — Directive text
```

### Obligation Levels

| Level | Keyword | Enforcement |
|-------|---------|-------------|
| **MUST** | Mandatory requirement | Hard deny if violated |
| **MUST NOT** | Absolute prohibition | Hard deny if violated |
| **SHOULD** | Strong recommendation | Review if unmet |
| **MAY** | Permission | Allowed |
| **SHOULD NOT** | Discouraged | Warning |

### Key Articles

| Article | Title | Focus |
|---------|-------|-------|
| **I** | Identity | Entity identity, immutability, uniqueness |
| **II** | Memory | Three categories, separation, TTL |
| **V** | Security | Access control, audit, threat levels |
| **XXXVI** | Evolution | 7-stage pipeline, safety, continuity |
| **LXVII** | Autonomy | Limited autonomy requirements |

### Evaluation Pipeline (7 Phases)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. REQUIRED FIELDS CHECK                                    │
│    → goal, scope, risk, audit_log present?                  │
├─────────────────────────────────────────────────────────────┤
│ 2. RESTRICTED ACTION CHECK                                  │
│    → modify_constitution, destroy_records, etc. → REVIEW    │
├─────────────────────────────────────────────────────────────┤
│ 3. CONSTITUTION MUST NOT CHECK                              │
│    → 93 prohibition rules → DENY if relevant               │
├─────────────────────────────────────────────────────────────┤
│ 4. YAML POLICY CHECKS                                       │
│    → Security, Evolution, Federation policies               │
├─────────────────────────────────────────────────────────────┤
│ 5. RISK-BASED EVALUATION                                    │
│    → Critical/High → REVIEW, Medium → MONITORED, Low → ALLOW│
├─────────────────────────────────────────────────────────────┤
│ 6. CORE PRINCIPLE CHECKS                                    │
│    → Limited Autonomy, Memory Separation, Controlled Evo   │
├─────────────────────────────────────────────────────────────┤
│ 7. OUTCOME DETERMINATION                                    │
│    → ALLOW / DENY / REVIEW with full audit trail           │
└─────────────────────────────────────────────────────────────┘
```

### Decision Outcomes

| Outcome | Meaning | When |
|---------|---------|------|
| **ALLOW** | Action proceeds | All checks pass, risk ≤ medium |
| **DENY** | Action blocked | Constitutional violation, policy violation, missing fields |
| **REVIEW** | Human approval required | High/critical risk, restricted action, unmet requirements |

---

## Core Subsystems

### 1. Orchestrator (`aios_core/orchestrator.py`)

Central coordination engine for multi-step tasks.

```python
orch = Orchestrator(db=Database(":memory:"), constitution_dir="...", policies_dir="...")

task = orch.create_task("analyze_data", "Analyze patterns", risk_level="low")
orch.add_step(task, "evaluate", params={"goal": "Read metrics", "scope": "analytics", "risk": "low"})
orch.add_step(task, "memory", params={"action": "store", "content": {...}, "category": "operational"})
orch.add_step(task, "reason", params={"question": "What does this imply?", "use_memory": True})
result = orch.execute_task(task)  # Constitutional check per step
```

**Step Types:** `evaluate`, `memory`, `knowledge`, `tool`, `reason`, `learn`, `evolve`, `approve`, `custom`

### 2. Constitution Engine (`aios_core/constitution_engine.py`)

Evaluates actions against 67 articles + 3 YAML policies.

```python
engine = ConstitutionEngine(constitution_dir="...", policies_dir="...")

result = engine.evaluate({
    "goal": "Deploy module",
    "scope": "production",
    "risk": "high",
    "audit_log": True,
    "agent_id": "deploy-agent",
    "authority": "operator",
})
# Returns: {decision: "REVIEW", reason: "risk_review", violations: [...], ...}
```

### 3. Memory Manager (`aios_core/memory_manager.py`)

Three constitutional categories with SQLite persistence.

```python
mm = MemoryManager(db=db)

# Personal - NEVER federated/shared
mm.store({"preferences": {...}}, category="personal")

# Operational - system procedures, lessons learned
mm.store({"procedure": "backup", "cron": "0 2 * * *"}, category="operational", tags=["ops"])

# Constitutional - immutable principles
mm.store({"principle": "Identity immutability"}, category="constitutional")

# Search
results = mm.search(query="backup", category="operational", tag="ops", limit=20)
```

### 4. Knowledge Graph (`aios_core/knowledge_graph.py`)

Nodes, typed edges, BFS traversal, pathfinding.

```python
kg = KnowledgeGraph(db=db)

n1 = kg.add_node("User", "entity", {"type": "actor"})
n2 = kg.add_node("Memory", "entity", {"type": "store"})
kg.add_relation(n1["id"], n2["id"], "owns", weight=1.0)

# Traverse
neighbors = kg.neighbors(n1["id"], depth=2)
path = kg.path(source_id, target_id)  # Shortest path (BFS)
```

### 5. Reasoning Engine (`aios_core/reasoning_engine.py`)

Multi-step explainable chains with memory/knowledge integration.

```python
re = ReasoningEngine(db=db, memory=mm, knowledge=kg)

chain = re.build_chain(
    question="Why scale at 8pm?",
    context={"pattern": "peak_8pm", "confidence": 0.92},
    use_memory=True,
    use_knowledge=True,
)
# Returns: {steps: [...], conclusion: "...", overall_confidence: 0.73}
```

### 6. Learning Engine (`aios_core/learning_engine.py`)

Experience recording → pattern extraction → recommendations.

```python
le = LearningEngine(db=db, memory=mm)

le.record({"task": "scaling", "action": "2x", "result": "latency -40%"}, tags=["success"])
patterns = le.extract_patterns()  # Successful patterns only
recs = le.get_recommendations({"task_name": "scaling"})  # Context-aware
```

### 7. Evolution Manager (`aios_core/evolution_manager.py`)

7-stage controlled evolution pipeline.

```python
em = EvolutionManager(db=db)

proposal = em.propose(
    change={"component": "reasoning_engine", "modification": "Add CoT"},
    component="reasoning_engine",
    reason="Improve accuracy"
)

# Stages: proposal → testing → sandbox → simulation → audit → approval → deployment
em.advance(proposal["id"])  # Next stage
em.approve(proposal["id"])  # At approval stage
em.can_deploy(proposal["id"])  # Check if deployable
```

### 8. Privacy Guard (`aios_core/privacy_guard.py`)

Data classification and access enforcement.

```python
pg = PrivacyGuard()
pg.classify({"user_id": "123", "email": "..."})  # → {classification: "personal", ...}
pg.check_access(agent_id, data_classification, action)  # → ALLOW/DENY
```

---

## Execution Pipeline

### Task Execution Flow

```
┌─────────────────┐
│ Create Task     │
│ (name, risk,    │
│  agent, auth)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Add Steps       │
│ (type, params,  │
│  name, desc)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Execute Task    │
│ (sequential)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ FOR EACH STEP:              │
│  1. Constitutional Check    │
│     → RuntimePolicy.eval()  │
│     → ALLOW/DENY/REVIEW     │
│  2. If DENY/REVIEW → stop   │
│  3. Execute step handler    │
│  4. Log to audit trail      │
│  5. Record learning (if OK) │
└─────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Return Summary  │
│ (status, steps, │
│  results, logs) │
└─────────────────┘
```

### Step Handlers

| Type | Handler | Description |
|------|---------|-------------|
| `evaluate` | `_step_evaluate` | Constitutional evaluation |
| `memory` | `_step_memory` | Store/retrieve/search/delete |
| `knowledge` | `_step_knowledge` | Add node/relation, find, neighbors |
| `reason` | `_step_reason` | Build reasoning chain |
| `learn` | `_step_learn` | Record learning experience |
| `evolve` | `_step_evolve` | Propose evolution |
| `tool` | `_step_tool` | Generic passthrough |
| `approve` | `_step_approve` | Pause for human approval |

---

## API Layers

### 1. REST API (Starlette) — Port 8000

**Base:** `http://localhost:8000`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/stats` | GET | Full system statistics |
| `/api/v1/evaluate` | POST | Constitutional evaluation |
| `/api/v1/constitution/stats` | GET | Constitution statistics |
| `/api/v1/tasks` | GET/POST | List/create tasks |
| `/api/v1/tasks/{id}` | GET | Get task details |
| `/api/v1/tasks/{id}/execute` | POST | Execute task |
| `/api/v1/memory` | GET/POST | Search/store memory |
| `/api/v1/memory/{id}` | GET/PUT/DELETE | CRUD memory item |
| `/api/v1/memory/stats` | GET | Memory statistics |
| `/api/v1/knowledge/nodes` | GET/POST | Find/add nodes |
| `/api/v1/knowledge/nodes/{id}` | GET | Get node |
| `/api/v1/knowledge/edges` | POST | Add relation |
| `/api/v1/knowledge/nodes/{id}/neighbors` | GET | Get neighbors |
| `/api/v1/knowledge/path` | GET | Find path |
| `/api/v1/knowledge/stats` | GET | KG statistics |
| `/api/v1/approvals` | GET | List pending approvals |
| `/api/v1/approvals/{id}/approve` | POST | Approve |
| `/api/v1/approvals/{id}/deny` | POST | Deny |
| `/api/v1/evolution/proposals` | GET/POST | List/create proposals |
| `/api/v1/evolution/proposals/{id}` | GET | Get proposal |
| `/api/v1/evolution/proposals/{id}/advance` | POST | Advance stage |
| `/api/v1/evolution/proposals/{id}/approve` | POST | Approve proposal |
| `/api/v1/evolution/proposals/{id}/reject` | POST | Reject proposal |
| `/api/v1/evolution/proposals/{id}/deploy-check` | GET | Can deploy? |
| `/api/v1/evolution/stats` | GET | Evolution statistics |
| `/api/v1/tests/suites` | GET | List test suites |
| `/api/v1/tests/run` | POST | Run all tests |
| `/api/v1/tests/run/{suite}` | POST | Run specific suite |
| `/api/v1/tests/last-report` | GET | Last test report |
| `/api/v1/tests/stats` | GET | Test engine statistics |
| `/api/v1/audit` | GET | Query audit log |
| `/api/v1/audit/stats` | GET | Audit statistics |
| `/rpc` | POST | JSON-RPC 2.0 bridge |

### 2. MCP Gateway (JSON-RPC 2.0) — Port 8471

**Endpoint:** `http://localhost:8471/rpc`

#### Protocol Methods

| Method | Description |
|--------|-------------|
| `initialize` | Handshake, returns capabilities |
| `ping` | Liveness check |
| `tools/list` | List available tools |
| `tools/call` | Execute tool (with constitutional guard) |
| `resources/list` | List resources |
| `resources/read` | Read resource |
| `prompts/list` | List prompt templates |
| `prompts/get` | Render prompt |
| `aios/evaluate` | Direct constitutional evaluation |
| `aios/approvals` | List pending approvals |
| `aios/stats` | Gateway statistics |

#### Built-in Tools

| Tool | Category | Risk | Description |
|------|----------|------|-------------|
| `aios_evaluate` | constitution | low | Evaluate action against constitution |
| `aios_memory_store` | memory | low | Store memory item |
| `aios_memory_search` | memory | low | Search memory |
| `aios_knowledge_query` | knowledge | low | Query knowledge graph |
| `aios_approve` | constitution | high | Approve pending action |
| `aios_deny` | constitution | high | Deny pending action |
| `aios_stats` | constitution | low | Get comprehensive stats |

#### Built-in Resources

| URI | Description |
|-----|-------------|
| `aios://constitution/overview` | Constitution summary |
| `aios://policies/summary` | Active policies |
| `aios://audit/recent` | Last 50 audit events |
| `aios://approvals/pending` | Pending approvals |

#### Built-in Prompts

| Name | Description |
|------|-------------|
| `evaluate_action` | Template for constitutional evaluation |
| `evolution_proposal` | Template for evolution proposal |

---

## Persistence Layer

### Database Schema (`aios_core/storage.py`)

```sql
-- Audit Events
CREATE TABLE audit_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    data TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    agent_id TEXT,
    decision TEXT,
    tags TEXT
);

-- Approvals
CREATE TABLE approvals (
    id TEXT PRIMARY KEY,
    action_data TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    requested_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT,
    timeout_seconds INTEGER DEFAULT 86400,
    evaluation_id TEXT,
    validation_data TEXT,
    metadata TEXT
);

-- Memory Items (3 categories)
CREATE TABLE memory_items (
    id TEXT PRIMARY KEY,
    category TEXT DEFAULT 'operational',  -- personal | operational | constitutional
    content TEXT NOT NULL,  -- JSON
    tags TEXT,
    source TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    expires_at TEXT,  -- TTL support
    access_count INTEGER DEFAULT 0,
    metadata TEXT
);

-- Knowledge Graph Nodes
CREATE TABLE kg_nodes (
    id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    label TEXT NOT NULL,
    properties TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

-- Knowledge Graph Edges
CREATE TABLE kg_edges (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES kg_nodes(id),
    target_id TEXT REFERENCES kg_nodes(id),
    relation TEXT NOT NULL,
    properties TEXT,
    weight REAL DEFAULT 1.0,
    created_at TEXT NOT NULL
);

-- Evolution Records
CREATE TABLE evolution_records (
    id TEXT PRIMARY KEY,
    evolution_type TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT,
    reason TEXT,
    expected_result TEXT,
    actual_result TEXT,
    stage TEXT,
    status DEFAULT 'proposed',
    proposed_at TEXT NOT NULL,
    completed_at TEXT,
    metadata TEXT
);

-- Schema Version
CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT);
```

### Configuration (`aios_core/config.py`)

```python
# Default paths (resolved relative to project root)
database.path = "aios.db"
constitution.dir = "docs/constitution"
policies.dir = "policies"
audit.retention_days = 90
approval.timeout_seconds = 86400
logging.level = "INFO"
```

---

## Testing & Self-Validation

### Test Engine (`aios_core/test_engine/`)

```python
engine = TestEngine(
    constitution_dir="docs/constitution",
    policies_dir="policies",
    db=Database(":memory:"),
)

# Run all built-in suites
report = engine.run_all()
print(engine.report_text(report))

# Run specific suite
suite = engine.run_suite("constitutional_compliance")

# Custom test case
from aios_core.test_engine.models import TestCase, TestCategory
custom = TestCase(
    name="my_test",
    category=TestCategory.SECURITY,
    action={"goal": "...", "scope": "...", "risk": "low", "audit_log": True, "agent_id": "a", "authority": "u"},
    expected_decision="DENY",
)
result = engine.run_case(custom)
```

### Built-in Suites (23 tests total)

| Suite | Tests | Focus |
|-------|-------|-------|
| `constitutional_compliance` | 13 | Core constitutional principles |
| `security_policy` | 4 | Security policy enforcement |
| `evolution_safety` | 3 | Evolution pipeline safety |
| `integration` | 3 | Cross-subsystem integration |

### Test Categories & Severities

```python
TestCategory: CONSTITUTIONAL, REGRESSION, INTEGRATION, PERFORMANCE, SECURITY, EVOLUTION
TestSeverity: CRITICAL, HIGH, MEDIUM, LOW
TestStatus: PENDING, RUNNING, PASSED, FAILED, ERROR, SKIPPED
```

---

## Evolution Pipeline

### 7 Stages

```
proposal → testing → sandbox → simulation → audit → approval → deployment
   │         │          │           │         │        │           │
   ▼         ▼          ▼           ▼         ▼        ▼           ▼
proposed  in_testing in_sandbox in_simulation in_audit pending_approval deploying
```

### Evolution Restrictions (from `policies/evolution_policy.yaml`)

| Restriction | Value | Meaning |
|-------------|-------|---------|
| `direct_core_modification` | prohibited | Cannot modify core directly |
| `unsafe_evolution` | blocked | Unsafe changes blocked |
| `constitution_changes` | approval_required | Constitution changes need approval |
| `breaking_changes` | human_review_required | Breaking changes need human review |

### Requirements

| Requirement | Value |
|-------------|-------|
| `testing_before_deployment` | true |
| `compatibility_check` | true |
| `constitutional_validation` | true |
| `rollback_capability` | required |

### Rollback Policy

- **Enabled:** true
- **Time limit:** 24 hours
- **Automatic on critical error:** true

---

## Security Model

### Threat Levels (from `policies/security_policy.yaml`)

| Level | Action | Escalation |
|-------|--------|------------|
| **critical** | immediate_isolation | human_review |
| **high** | restricted_operation | audit_and_review |
| **medium** | monitored_operation | logging |
| **low** | standard_operation | background_monitoring |

### Security Rules

| Rule | Enforcement |
|------|-------------|
| `least_privilege` | Unlimited authority → DENY |
| `unknown_access_blocked` | agent_id="unknown" → DENY |
| `audit_logging` | audit_log=false → DENY |
| `security_events_tracked` | All events logged |

### Federation Rules (`policies/federation_policy.yaml`)

| Rule | Enforcement |
|------|-------------|
| `verified_nodes_only` | Unverified node → DENY |
| `synchronization_audit_required` | All syncs audited |
| `inconsistent_state_requires_review` | Conflicts → REVIEW |

### Sync Frequencies

| Type | Frequency |
|------|-----------|
| `critical_policies` | immediate |
| `security_updates` | hourly |
| `constitution_updates` | on_demand |
| `operational_state` | periodic |

---

## Quick Reference

### Import All

```python
from aios_core import (
    Orchestrator, Database, TaskStatus, StepStatus,
    ConstitutionLoader, ConstitutionEngine, ObligationLevel,
    MemoryManager, KnowledgeGraph, ReasoningEngine,
    LearningEngine, EvolutionManager, PrivacyGuard,
    RuntimePolicy, ApprovalManager, AuditLogger,
    create_app, AIOSAPI,
    TestEngine, TestRunner, TestReporter,
    TestCase, TestResult, TestSuiteResult, TestReport,
    TestStatus, TestSeverity, TestCategory,
    constitutional_compliance_suite, security_policy_suite,
    evolution_safety_suite, integration_suite,
    MCPGateway, GatewayConfig, ConstitutionGuard,
    MCPProtocol, JSONRPCRequest, JSONRPCResponse,
    ToolDefinition, ToolRegistry, ResourceDefinition, ResourceRegistry,
    PromptDefinition, PromptRegistry,
)
```

### Minimal Working Example

```python
from aios_core import Orchestrator, Database

db = Database(":memory:")
orch = Orchestrator(db=db)

# Evaluate
result = orch.evaluate({
    "goal": "Read metrics", "scope": "monitoring",
    "risk": "low", "audit_log": True,
    "agent_id": "agent-1", "authority": "user",
})
print(result["decision"])  # ALLOW

# Task
task = orch.create_task("demo", "Demo task", risk_level="low")
orch.add_step(task, "memory", params={
    "action": "store", "content": {"demo": True}, "category": "operational"
})
result = orch.execute_task(task)
print(result["status"])  # completed

db.close()
```

### Running Servers

```bash
# REST API (port 8000)
python run_rest_api.py --host 0.0.0.0 --port 8000

# MCP Gateway (port 8471)
python run_mcp_server.py --host 0.0.0.0 --port 8471

# Run tests
python -m pytest tests/ -v
```

### Key Files

```
aios/
├── aios_core/                    # Core implementation
│   ├── __init__.py               # Exports all public APIs
│   ├── orchestrator.py           # Task orchestration
│   ├── constitution_engine.py    # 7-phase evaluation
│   ├── constitution_loader.py    # Article parsing
│   ├── constitution_validator.py # Validation
│   ├── runtime_policy.py         # Policy enforcement
│   ├── policy_loader.py          # YAML policy loading
│   ├── storage.py                # SQLite persistence
│   ├── config.py                 # Configuration
│   ├── memory_manager.py         # 3-category memory
│   ├── knowledge_graph.py        # Graph DB
│   ├── reasoning_engine.py       # Explainable reasoning
│   ├── learning_engine.py        # Experience learning
│   ├── evolution_manager.py      # 7-stage pipeline
│   ├── privacy_guard.py          # Data classification
│   ├── audit_logger.py           # Audit trail
│   ├── approval_manager.py       # Human approvals
│   ├── api/app.py                # REST API (Starlette)
│   ├── mcp/gateway.py            # MCP JSON-RPC 2.0
│   ├── mcp/protocol.py           # Protocol types
│   ├── mcp/tools.py              # Tool registry
│   ├── mcp/resources.py          # Resource registry
│   ├── mcp/prompts.py            # Prompt registry
│   └── test_engine/              # Self-test framework
├── docs/constitution/            # 67 Article markdown files
├── policies/                     # 3 YAML policy files
├── tests/                        # 438 tests
├── run_rest_api.py               # REST API server
├── run_mcp_server.py             # MCP Gateway server
├── demo.py                       # Full demonstration
├── requirements.txt              # Dependencies
└── ARCHITECTURE.md               # This file
```

---

## License & Credits

**AIOS** — Self-Evolving Distributed Operating System for Application Intelligence
Powered by **Octopus Runtime** | Constitutional Governance v3.1.0

*Every action has a constitutional basis. Every evolution preserves identity.*