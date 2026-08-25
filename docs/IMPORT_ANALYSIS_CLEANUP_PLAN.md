# Import Analysis & Circular Dependency Cleanup

## Goal
Prepare AIOS for clean production architecture by identifying and removing unhealthy dependency paths.

## Steps

1. Build import map
2. Detect circular dependencies
3. Classify modules:
   - Core Runtime
   - Orchestration
   - Agents
   - Tools
   - Memory
   - Infrastructure
4. Move infrastructure dependencies outward
5. Keep core modules independent
6. Validate with tests

## Rules

- Core must not depend on deployment details.
- Agents must use interfaces instead of direct infrastructure calls.
- Tools must remain isolated and replaceable.
- Memory access goes through defined contracts.

## Output

Dependency issues are tracked before refactoring commits begin.
