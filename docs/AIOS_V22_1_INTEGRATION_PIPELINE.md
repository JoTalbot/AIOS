# AIOS v22.1 Cognitive Integration Pipeline

## Added

- Event Bus Adapter
- Memory Adapter
- Cognitive workflow integration boundaries

## Flow

AIOS Runtime -> Runtime Adapter -> Cognitive Registry -> Event Bus -> Services -> Memory Layer

## Goals

- Keep runtime isolation
- Enable event-driven cognitive workflows
- Provide replaceable memory backends
