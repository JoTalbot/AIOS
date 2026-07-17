# AIOS MCP Architecture

## Purpose

Define the external integration layer of AIOS based on Model Context Protocol (MCP).

MCP provides a universal interface allowing external applications, agents, dashboards and bots to connect with AIOS capabilities.

## Core Principle

AIOS is not a closed application.

It is an intelligence operating system that exposes controlled access to knowledge, planning, capabilities and execution through MCP.

## MCP Role

MCP acts as the communication bridge between AIOS and external systems.

Examples:

- Telegram bots;
- dashboards;
- AI agents;
- mobile applications;
- developer tools;
- external automation systems.

## Architecture

```
External Application
        |
        |
    MCP Client
        |
        |
    AIOS MCP Server
        |
 +------+------+------+ 
 |      |      |      |
Knowledge Planner Capability Workers
```

## MCP Server Responsibilities

The AIOS MCP Server provides:

- capability discovery;
- API registry access;
- task creation;
- planning requests;
- execution control;
- experience retrieval;
- system status information.

## Capability Exposure

External applications do not directly control workers.

They request capabilities:

```
Application
    |
    ↓
MCP Request
    |
    ↓
Capability Selection
    |
    ↓
Execution
    |
    ↓
Result
```

## Application Integration

Any application can become an AIOS project entry point.

Examples:

```
Text skill
APK application
Play Market URL
Web application
API service
```

Application lifecycle:

```
Submitted
 ↓
Discovered
 ↓
Registered
 ↓
Analyzed
 ↓
Tested
 ↓
Integrated
 ↓
Monitored
```

## API Registry

AIOS maintains information about connected APIs:

```
API
 - version
 - status
 - owner
 - dependencies
 - tests
 - metrics
 - availability
```

Operations:

- enable;
- disable;
- test;
- update;
- rollback;
- mass orchestration.

## Context Exchange

MCP transfers relevant context:

- task information;
- permissions;
- knowledge objects;
- previous experience;
- execution results.

## Security Model

External systems receive controlled access through:

- authentication;
- authorization;
- capability permissions;
- audit events.

## Principle

MCP is the universal interface of AIOS.

Any compatible application can become a client, while AIOS remains the central intelligence and orchestration layer.
