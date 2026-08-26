# AIOS v22.4 Agent Loop

## Cognitive Execution Cycle

Goal -> Context -> Reasoning -> Planning -> Action -> Reflection

## Components

- ReasoningEngine: evaluates context and produces reasoning state.
- ActionPlanner: converts reasoning state into executable plans.

## Design Rules

- Keep runtime isolated.
- Use existing cognitive contracts.
- Allow future autonomous agent execution.
