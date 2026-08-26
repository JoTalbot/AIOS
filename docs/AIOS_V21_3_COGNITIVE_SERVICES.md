# AIOS v21.3 Cognitive Services Layer

## Purpose
Define the first implementation boundary for the v21 cognitive architecture.

## Services

### Knowledge Graph Service
Responsibilities:
- Entity storage
- Relationship traversal
- Semantic context retrieval

### Belief Service
Responsibilities:
- Confidence scoring
- Evidence tracking
- Belief updates

### Context Orchestrator
Responsibilities:
- Context assembly
- Priority ranking
- Agent input preparation

### Reflection Service
Responsibilities:
- Execution review
- Pattern extraction
- Improvement proposals

## Runtime Contract

All services communicate through stable internal APIs.
No direct coupling with platform adapters.
No replacement of existing v20 execution paths.

## Next Build Phase

- Create service interfaces.
- Add persistence schemas.
- Add unit tests.
- Connect to cognitive loop.
