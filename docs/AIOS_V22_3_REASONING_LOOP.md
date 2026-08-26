# AIOS v22.3 Reasoning Loop

## Components

- Goal Manager
- Task Decomposition Engine
- Workflow Engine
- Cognitive Services

## Flow

Goal -> Decompose -> Context -> Reason -> Action -> Reflection

## Design Rules

- Keep reasoning isolated from runtime execution.
- Use existing registry and event bus boundaries.
- Maintain replaceable cognitive modules.
