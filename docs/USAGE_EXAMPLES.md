# AIOS Usage Examples

## Basic Constitutional Decision Making

```python
from aios_core import ConstitutionEngine

engine = ConstitutionEngine()

# Valid action
action = {
    "goal": "analyze_data",
    "scope": "local_node",
    "risk": "low",
    "audit_log": True
}

result = engine.evaluate(action)
print(f"Decision: {result['decision']}")
# Output: Decision: ALLOW
```

## Runtime Policy Enforcement

```python
from aios_core import RuntimePolicy

policy = RuntimePolicy()

agent_action = {
    "goal": "deploy_model",
    "scope": "cluster",
    "risk": "high",
    "audit_log": True
}

result = policy.request_execution(agent_action)

if result["allowed"]:
    print("Executing action...")
else:
    print(f"Action blocked: {result['details']}")
```

## Learning Management

```python
from aios_core import LearningEngine

learner = LearningEngine()

# Record successful experience
experience = {
    "action": "optimize_query",
    "outcome": "success",
    "improvement": 15.3,
    "confidence": 0.92
}

learner.learn(experience)

# Extract patterns
patterns = learner.extract_patterns()
for pattern in patterns:
    print(f"Pattern: {pattern['action']} -> {pattern['outcome']}")
```

## Evolution Management

```python
from aios_core import EvolutionManager

manager = EvolutionManager()

# Propose change
change = {
    "component": "security_policy",
    "modification": "add_token_validation",
    "risk_level": "low"
}

proposal = manager.create_proposal(change)
print(f"Proposal ID: {proposal}")

# Advance through stages
manager.advance_stage(0)  # Move to sandbox
manager.advance_stage(0)  # Move to simulation
manager.advance_stage(0)  # Move to audit
manager.advance_stage(0)  # Move to approval

# Check if can deploy
if manager.can_deploy(audit_passed=True, approved=True):
    manager.advance_stage(0)  # Move to deployment
    print("Change deployed successfully")
```

## Approval Workflows

```python
from aios_core import ApprovalManager

approver = ApprovalManager()

# Request critical action approval
action = {
    "action": "modify_core_policy",
    "impact": "high",
    "reversible": False
}

approval = approver.request(action)
print(f"Approval requested: {approval['status']}")

# Approve
approver.approve(0)
print("Action approved")
```

## Privacy Protection

```python
from aios_core import PrivacyGuard

guard = PrivacyGuard()

# Check if data can be shared
request = {
    "data": "user_profile",
    "classification": "PERSONAL"
}

result = guard.check_access(request)
if result["allowed"]:
    print("Data can be shared")
else:
    print(f"Access denied: {result['reason']}")
```

## Memory Management

```python
from aios_core import MemoryManager

mem = MemoryManager()

# Store operational memory
mem.store(
    {"procedure": "backup_routine", "frequency": "daily"},
    category="operational"
)

# Store constitutional memory
mem.store(
    {"principle": "human_oversight", "immutable": True},
    category="constitutional"
)

# Search memory
results = mem.search("backup")
print(f"Found {len(results)} results")
```

## Audit Logging

```python
from aios_core import AuditLogger

logger = AuditLogger()

# Record action
logger.record({
    "type": "constitutional_decision",
    "action": "approve_deployment",
    "result": "ALLOW",
    "reasoning": "action complies with principles"
})

# Query audit log
events = logger.query(event_type="constitutional_decision")
for event in events:
    print(f"{event['timestamp']}: {event['result']}")
```
