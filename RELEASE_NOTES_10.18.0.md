# AIOS Release Notes — v10.18.0 (Async Horizon & Federated Edge)

## 🎯 Executive Summary
Release **v10.18.0** delivers the ultimate scaling architecture for AIOS. We successfully migrated all core storage layers to full native asynchronous execution and established the foundation for decentralized, privacy-preserving AI through WebAssembly sandboxing and Advanced Federated Learning.

## ⚡ Core Async Architecture
- **True Asyncpg & Aiosqlite Migration**: Completely rewrote the `AsyncDatabase` wrapper. It now drops the blocking `asyncio.to_thread` facade in favor of native non-blocking database drivers. 
- **Dynamic Query Translation**: Implemented a real-time dialect translator that seamlessly maps SQLite `?` bindings to PostgreSQL `$1, $2` parameters, ensuring total cross-database compatibility without changing application code.
- **Uncompromised Performance**: Maintains extreme throughput (~234,000+ OPS) while eliminating thread-pool starvation under massive I/O loads.

## 🛡️ WebAssembly Plugin Sandbox
- **Wasm Runtime Integration**: Introduced `WasmRuntime` into the Plugin Manager (v5.0).
- **Secure Isolation**: External and untrusted plugins can now be compiled to `.wasm` and executed with zero access to the host's memory, filesystem, or network.
- **Boundary Hooks**: Native AIOS events can now trigger Wasm hooks, dynamically serializing payloads across the WebAssembly execution boundary.

## 🌐 Edge Federated Learning (FL)
- **Asynchronous Aggregation (FedAsync)**: Replaced strict synchronous rounds. The coordinator now gracefully blends stale model gradients from lagging edge devices based on a time-decay alpha factor.
- **Secure Aggregation (SecAgg)**: Server no longer sees raw client updates. Gradients are mathematically masked on the client and only unmasked upon full aggregation.
- **Local Differential Privacy (LDP)**: Enabled customizable Gaussian noise injection at the device level, constrained by a strict Epsilon budget.
- **Hardware-Aware Client Selection**: The FL coordinator profiles nodes and selects participants dynamically based on compute capacity (`GFLOPS`) and remaining battery life.

---
**Status:** ✅ Released
