# AIOS v22.0 Cognitive Pipeline

## Overview

v22.0 introduces the first stable cognitive pipeline layer.

## Components

- Event Bus: asynchronous communication between cognitive services.
- Memory Layer: persistent abstraction for cognitive state.
- Registry Integration: service discovery through existing bootstrap.

## Flow

Runtime -> Adapter -> Registry -> Event Bus -> Cognitive Services -> Memory

## Design Rules

- Keep runtime isolated.
- Preserve service contracts.
- Allow independent cognitive evolution.
