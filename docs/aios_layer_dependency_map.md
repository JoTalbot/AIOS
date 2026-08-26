# AIOS Layer Dependency Map

## Current Foundation

Runtime
→ Meta-Kernel
→ Federation Layer
→ Digital Twin Layer

## Dependency Rules

- Lower layers must remain independent of higher layers.
- New capabilities should integrate through explicit interfaces.
- Agents must update documentation with architectural decisions.
- Parallel agents must commit incremental progress immediately.

## Integration Direction

Digital Twin provides prediction and simulation.
Federation provides distributed coordination.
Meta-Kernel provides orchestration.

Future layers should consume these capabilities without breaking existing contracts.

## Agent Handoff

Before changing architecture:
1. Read current repository state.
2. Review existing interfaces.
3. Add tests.
4. Commit changes.
5. Document migration impact.
