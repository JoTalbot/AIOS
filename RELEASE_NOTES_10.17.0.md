# AIOS Release Notes — v10.17.0 (Next-Gen Memory & Substrate UI)

## 🎯 Executive Summary
Following the massive stability and infrastructure improvements in v10.16.0, release **v10.17.0** focuses on scaling agent memory capabilities and enhancing deep-tech observability. We introduced native vector compression for long-term agent memory, deployed a visual substrate convergence router, and hardened our AWS EKS monitoring stack.

## 🧠 Agent Memory Optimization
- **Vector Compression (PQ)**: Implemented Product Quantization compression natively in pure Python within `vector_store.py`. This scales down memory consumption of high-dimensional embeddings by ~75% via `uint8` codebook quantization.
- **Semantic Search Integration**: `MemoryManager` now performs hybrid semantic searches out-of-the-box. Any stored memory with an `embedding` metadata tag is automatically indexed into the compressed vector store and can be retrieved using the new `semantic_search()` method.

## 🌌 Substrate Convergence Dashboard UI
- Built an interactive, dark-mode native HTML/JS dashboard (`dashboard/substrate.html`).
- Features a **Live Dispatch Router** visualizing the `SubstrateConvergenceEngine` actively routing workloads (inference, optimization, parallel) across Silicon, Photonic, Neuromorphic, Quantum, and Bio-Compute mesh nodes.
- Tracks real-time substrate health, efficiency metrics (GFLOPS/W), latency, and dynamic failover states.

## 🔔 Enterprise Infrastructure Observability
- Added comprehensive alerting rules to `production-alerts.yml` for Prometheus/Datadog targeting the new AWS infrastructure:
  - **EKS Node CPU Utilization**: Alerts on >85% cluster compute saturation.
  - **RDS PostgreSQL Connection Pooling**: Monitors active connection leaks.
  - **ElastiCache Redis Memory**: Tracks memory exhaustion before eviction policies drop critical task queues.
  - **CrashLoopBackOff Detection**: Real-time alerts for recurring API pod crashes.

---
**Status:** ✅ Released
