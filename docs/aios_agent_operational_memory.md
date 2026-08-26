# AIOS Agent Operational Memory Protocol

## Purpose

Maintain a persistent operational memory inside the repository so parallel AI agents can continue work safely.

## Rules

- Repository state is the source of truth.
- Every meaningful implementation step is committed.
- Architecture decisions are documented.
- Tests accompany implementation changes.
- Agents must inspect existing layers before extending them.

## Current Foundation

- Runtime
- Meta-Kernel
- Federation Layer
- Digital Twin Layer
- Knowledge Synchronization
- Validation and Handoff

## Continuation

Future agents should update this document when changing architecture, migration strategy, or integration boundaries.
