# AIOS Dependency Audit Plan

Branch: clean-code-production

## Goals

- map module dependencies;
- identify circular imports;
- separate core runtime from infrastructure;
- remove unnecessary coupling;
- prepare production baseline.

## Audit Steps

1. Dependency graph generation
2. Import cycle detection
3. Layer boundary validation
4. External dependency review
5. Cleanup candidates list
6. Refactoring plan

## Target Architecture

Core -> Services -> Agents -> Tools -> Infrastructure

Dependencies should flow inward and avoid reverse coupling.
