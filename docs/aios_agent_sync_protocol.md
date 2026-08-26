# AIOS Agent Synchronization Protocol

## Purpose

Define how parallel AI agents continue development without losing architectural context.

## Rules

- Read repository state before changes.
- Preserve existing interfaces.
- Commit every meaningful step.
- Keep status documentation updated.
- Add tests with implementation changes.
- Record migration decisions.

## Current Foundation

- Federation Layer
- Digital Twin Layer
- Meta-Kernel integration points
- Knowledge synchronization
- Validation and handoff process

## Agent Handoff

Each agent must leave enough repository context for the next agent to continue from the latest committed state.
