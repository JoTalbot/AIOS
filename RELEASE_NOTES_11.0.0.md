# AIOS Release Notes — v11.0.0 (The Quantum Paradigm)

## 🎯 Executive Summary
Welcome to **AIOS v11.0.0** — the largest and most ambitious release in the history of the framework. This major version officially transitions AIOS into a distributed gRPC microservice architecture, pioneers the first implementation of Quantum Error Mitigation (QEM) in our quantum module, and publicly launches the AIOS Developer SDK.

## 📡 gRPC Microservices Core
- **Framework Transition**: AIOS Core is now fully exposed as a high-performance gRPC service. 
- **`AiosCore` Service**: Implemented `SubmitTask`, `GetTaskStatus`, and `GetStats` via `.proto` definitions. This enables lightning-fast, typed communications across large-scale distributed deployments.
- **Microservice Ready**: You can now spin up standalone AIOS orchestrators and interact with them in microseconds, completely bypassing HTTP overhead.

## 🔮 Quantum Error Mitigation (QEM)
- **Zero-Noise Extrapolation (ZNE)**: Added advanced quantum noise compensation. AIOS now artificially scales depolarization noise (`noise_factor`), extrapolating results back to a theoretical zero-noise state using Richardson extrapolation.
- **Readout Error Correction**: Integrated measurement mitigation using Confusion Matrix inversion (Pseudo-inverse), successfully suppressing SPAM (State Preparation and Measurement) noise.
- **Noisy Circuit Simulations**: The `QuantumCircuit` simulator now supports injecting physical hardware noise models.

## 📦 AIOS Public Developer Platform & SDK
- **Pip Package**: The `aios-client` is now officially ready for public PyPI distribution via standard `pyproject.toml` setups.
- **gRPC + REST Support**: The SDK natively supports both standard REST async requests (`httpx`) and `grpc` channel stubs out of the box.
- **Documentation**: Added comprehensive `SDK_QUICKSTART.md` allowing developers to connect and orchestrate AIOS tasks in under 10 lines of code.

---
**Status:** ✅ Released
