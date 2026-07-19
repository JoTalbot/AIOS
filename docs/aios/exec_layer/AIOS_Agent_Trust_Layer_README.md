# AIOS Agent Trust Layer v2.1.1

## Purpose

Provides identity, reputation and capability control for AIOS agents.

## Components

- trust_manager.py
  - evaluates agent trust score

- agent_reputation.yaml
  - stores reputation metrics

- capability_policy.yaml
  - defines capability boundaries

## Principles

- Least privilege
- Audit before expansion
- High-risk actions require approval
