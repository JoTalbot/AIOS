# Real Import Graph Analysis Plan

## Goal
Build the factual dependency graph of AIOS modules before production refactoring.

## Analysis Steps

1. Discover all Python modules.
2. Extract import relationships.
3. Build directed dependency graph.
4. Detect circular dependencies.
5. Identify high-coupling modules.
6. Prepare safe refactoring batches.

## Validation Rules

- Core Runtime must remain independent.
- Infrastructure dependencies must not leak into core.
- Agents should depend on interfaces.
- External integrations must remain isolated.

## Output

The analysis produces:

- dependency graph
- cycle report
- refactoring candidates
- migration order
