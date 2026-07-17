# AIOS MCP Architecture

## Purpose

Define the external control interface of AIOS.

MCP is the unified access layer through which Telegram bots, dashboards, agents and external systems communicate with AIOS capabilities.

## Core Principle

External users interact with one intelligent interface while internal execution remains distributed.

```
External Client
      |
      v
AIOS MCP Gateway
      |
      v
Orchestrator
      |
+-----+-----+-----+
|     |     |     |
Cell  Cell  Cell  Cell
```

## Supported Clients

AIOS MCP may serve:

- Telegram bots
- dashboards
- AI agents
- developer tools
- automation systems

## Capability Registry

The MCP layer maintains knowledge about:

- available APIs
- active skills
- application profiles
- worker states
- testing progress
- capability maturity

## API Federation

Multiple internal workers can be combined into one external API.

Example:

```
External Request
        |
        v
Orchestrator
        |
+-------+-------+
|               |
Worker A       Worker B
Search API     Messaging API
        |
        v
Unified Capability
```

## Dynamic Control

AIOS MCP should support:

- enable/disable capabilities
- route requests
- monitor execution
- select workers
- update skills
- expose new functions

## Distributed Deployment

AIOS is not limited to one server.

Possible deployment:

```
Server A
 - MCP Gateway
 - Orchestrator

Server B
 - Android Test Cells

Server C
 - Memory Nodes

Server D
 - Specialized Workers
```

## Core Principle

MCP is the nervous system of AIOS, connecting distributed intelligence into one controllable platform.
