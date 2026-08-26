# AIOS vNext Architecture

AIOS is a modular operating system architecture for autonomous agents.

## Core layers

- Kernel: scheduling, context, memory, lifecycle
- Agents: planning and execution processes
- Cognition: reflection and learning loops
- Communication: agent message bus
- Security: sandbox and permissions
- Tools: controlled external actions
- LLM: provider abstraction
- Runtime: boot and orchestration

## Execution flow

Intent -> Planner -> Scheduler -> Agent -> Tools -> Memory -> Reflection
