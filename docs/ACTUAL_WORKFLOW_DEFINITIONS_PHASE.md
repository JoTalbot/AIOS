# Actual Workflow Definitions Phase

## Goal
Move from CI design to concrete GitHub Actions workflow definitions.

## Pipeline

```
Commit
  |
  v
GitHub Actions
  |
  +-- Unit Tests
  +-- Runtime Validation
  +-- Regression Suite
  +-- Architecture Checks
  |
  v
Production Candidate
```

## Requirements

- Define workflow triggers.
- Run automated validation on changes.
- Block promotion on failures.
- Keep production builds reproducible.

## Rules

- CI is the required quality gate.
- Core Runtime validation runs automatically.
- Regression failures prevent release progression.
- Production candidate creation requires green checks.

## Current Phase

- Workflow specification documented.
- Next step: create actual `.github/workflows` definitions.
