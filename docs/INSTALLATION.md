# AIOS Installation and Setup Guide

## Requirements

- Python 3.8+
- pip or conda
- Git

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/JoTalbot/AIOS.git
cd AIOS
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

### Import AIOS Core

```python
from aios_core import ConstitutionEngine, RuntimePolicy

# Create engine
engine = ConstitutionEngine()

# Evaluate action
action = {
    "goal": "system_check",
    "scope": "local_node",
    "risk": "low",
    "audit_log": True
}

result = engine.evaluate(action)
print(result)
# Output: {"decision": "ALLOW", "reason": "constitutional_compliance", ...}
```

## Running Tests

```bash
python -m pytest tests/
```

## Configuration

Edit `constitution/core_principles.md` to customize constitutional rules.

Edit policy files in `policies/` directory to configure:
- Security policies
- Federation rules
- Evolution constraints
- Memory management

## Deployment

For production deployment, follow the Evolution Manager pipeline:

1. **Proposal** - Create change proposal
2. **Sandbox** - Test in isolated environment
3. **Simulation** - Run simulations
4. **Audit** - Audit review
5. **Approval** - Require approval
6. **Deployment** - Deploy to production

See `docs/DEPLOYMENT.md` for detailed instructions.
