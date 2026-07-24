"""Universal Substrate-Agnostic Execution Engine for AIOS Horizon 8.0.

Dispatches workloads dynamically across Silicon (CPU/GPU), Photonic (Optical),
Neuromorphic (SNN), Quantum (QPU), and Biological compute runtimes.

Features:
- Multi-substrate registration and health monitoring
- Energy-aware scheduling with efficiency optimization
- Task queue with priority and substrate affinity
- Automatic failover on substrate failure
- Load balancing across substrates
- Dispatch history and energy accounting
- Workload profiling and substrate benchmarking
"""

import time
from collections import defaultdict
from typing import Any

__all__ = ["SubstrateConvergenceEngine", "SubstrateType"]


class SubstrateType:
    """Substrate type constants."""

    SILICON = "silicon_x86_arm"
    PHOTONIC = "photonic_optical"
    NEUROMORPHIC = "neuromorphic_snn"
    QUANTUM = "quantum_qpu"
    BIO_COMPUTE = "bio_compute"

    ALL = [SILICON, PHOTONIC, NEUROMORPHIC, QUANTUM, BIO_COMPUTE]


class SubstrateConvergenceEngine:
    """Substrate-Agnostic Unified Execution Router.

    Features:
    - Substrate registration with efficiency and latency metrics
    - Energy-aware optimal substrate selection
    - Priority task queue with substrate affinity
    - Automatic failover when a substrate becomes unavailable
    - Load balancing across active substrates
    - Dispatch history and energy accounting
    - Substrate health monitoring and benchmarking
    """

    def __init__(self):
        """Initialize SubstrateConvergenceEngine."""
        self.substrates: dict[str, dict[str, Any]] = {
            SubstrateType.SILICON: {
                "type": SubstrateType.SILICON,
                "latency_base_ms": 5.0,
                "efficiency_gflops_per_watt": 100.0,
                "energy_cost_per_unit": 0.10,
                "active": True,
                "capacity": 1000,
                "current_load": 0,
                "health": 1.0,
                "task_affinity": ["compute", "io", "general"],
            },
            SubstrateType.PHOTONIC: {
                "type": SubstrateType.PHOTONIC,
                "latency_base_ms": 0.05,
                "efficiency_gflops_per_watt": 10000.0,
                "energy_cost_per_unit": 0.01,
                "active": True,
                "capacity": 500,
                "current_load": 0,
                "health": 1.0,
                "task_affinity": ["signal", "matrix", "parallel"],
            },
            SubstrateType.NEUROMORPHIC: {
                "type": SubstrateType.NEUROMORPHIC,
                "latency_base_ms": 0.20,
                "efficiency_gflops_per_watt": 5000.0,
                "energy_cost_per_unit": 0.05,
                "active": True,
                "capacity": 300,
                "current_load": 0,
                "health": 1.0,
                "task_affinity": ["learn", "adapt", "inference"],
            },
            SubstrateType.QUANTUM: {
                "type": SubstrateType.QUANTUM,
                "latency_base_ms": 1.0,
                "efficiency_gflops_per_watt": 2000.0,
                "energy_cost_per_unit": 0.50,
                "active": True,
                "capacity": 50,
                "current_load": 0,
                "health": 1.0,
                "task_affinity": ["search", "optimization", "crypto"],
            },
            SubstrateType.BIO_COMPUTE: {
                "type": SubstrateType.BIO_COMPUTE,
                "latency_base_ms": 50.0,
                "efficiency_gflops_per_watt": 50000.0,
                "energy_cost_per_unit": 0.02,
                "active": True,
                "capacity": 100,
                "current_load": 0,
                "health": 1.0,
                "task_affinity": ["evolve", "self_repair", "pattern"],
            },
        }
        self.dispatch_history: list[dict[str, Any]] = []
        self._task_queue: list[dict[str, Any]] = []
        self._energy_account: dict[str, float] = defaultdict(float)
        self._substrate_failover_count: dict[str, int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Substrate management
    # ------------------------------------------------------------------

    def register_substrate(
        self,
        substrate_type: str,
        latency_base_ms: float = 5.0,
        efficiency_gflops_per_watt: float = 100.0,
        energy_cost_per_unit: float = 0.1,
        capacity: int = 500,
        task_affinity: list[str] = [],
    ) -> dict[str, Any]:
        """Register a new compute substrate."""
        record = {
            "type": substrate_type,
            "latency_base_ms": latency_base_ms,
            "efficiency_gflops_per_watt": efficiency_gflops_per_watt,
            "energy_cost_per_unit": energy_cost_per_unit,
            "active": True,
            "capacity": capacity,
            "current_load": 0,
            "health": 1.0,
            "task_affinity": task_affinity,
        }
        self.substrates[substrate_type] = record
        return record

    def set_substrate_active(self, substrate_type: str, active: bool) -> bool:
        """Activate or deactivate a substrate."""
        sub = self.substrates.get(substrate_type)
        if sub is None:
            return False
        sub["active"] = active
        return True

    def update_substrate_health(self, substrate_type: str, health: float) -> bool:
        """Update health score (0.0–1.0) for a substrate."""
        sub = self.substrates.get(substrate_type)
        if sub is None:
            return False
        sub["health"] = max(0.0, min(1.0, health))
        # Auto-deactivate if health drops below threshold
        if health < 0.2:
            sub["active"] = False
        return True

    # ------------------------------------------------------------------
    # Optimal substrate selection
    # ------------------------------------------------------------------

    def select_optimal_substrate(self, task_requirements: dict[str, Any]) -> str:
        """Select compute substrate optimizing energy efficiency, latency, and affinity.

        Priority:
        1. Preferred type if specified and available
        2. Substrate matching task affinity
        3. Highest energy efficiency active substrate
        """
        req_type = task_requirements.get("preferred_type")
        req_category = task_requirements.get("category", "general")

        # Check preferred type
        if req_type and req_type in self.substrates:
            sub = self.substrates[req_type]
            if sub["active"] and sub["health"] > 0.5:
                return req_type

        # Check affinity match
        best_affinity: tuple[float, str] | None = None
        for sub in self.substrates.values():
            if not sub["active"] or sub["health"] < 0.5:
                continue
            if req_category in sub.get("task_affinity", []):
                # Score: efficiency * health * (1 / latency) * available_capacity
                available = sub["capacity"] - sub["current_load"]
                score = (
                    sub["efficiency_gflops_per_watt"]
                    * sub["health"]
                    * (1.0 / max(0.001, sub["latency_base_ms"]))
                    * (available / max(1, sub["capacity"]))
                )
                if best_affinity is None or score > best_affinity[0]:
                    best_affinity = (score, sub["type"])

        if best_affinity:
            return best_affinity[1]

        # Fallback: highest efficiency active substrate
        active = [
            s for s in self.substrates.values() if s["active"] and s["health"] > 0.5
        ]
        if not active:
            # Emergency: use any substrate regardless of health
            active = list(self.substrates.values())
        if not active:
            return SubstrateType.SILICON

        optimal = max(
            active,
            key=lambda x: x["efficiency_gflops_per_watt"] * x["health"],
        )
        return optimal["type"]

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    def submit_task(
        self,
        task: dict[str, Any],
        priority: int = 0,
    ) -> dict[str, Any]:
        """Submit a task to the priority queue for execution."""
        task_id = task.get("id", f"s_task_{len(self._task_queue)}")
        task_record = {
            "task_id": task_id,
            "task": task,
            "priority": priority,
            "submitted_at": time.time(),
            "status": "queued",
        }
        self._task_queue.append(task_record)
        # Sort by priority (lower = higher priority)
        self._task_queue.sort(key=lambda t: t["priority"])
        return task_record

    def execute_substrate_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute task on optimal substrate."""
        start_time = time.time()
        substrate_type = self.select_optimal_substrate(task)
        sub_info = self.substrates[substrate_type]

        # Update load
        sub_info["current_load"] += 1

        # Compute energy cost
        energy_units = task.get("compute_units", 1)
        energy_cost = energy_units * sub_info["energy_cost_per_unit"]
        self._energy_account[substrate_type] += energy_cost

        dispatch_record = {
            "task_id": task.get("id", f"s_task_{len(self.dispatch_history)}"),
            "selected_substrate": substrate_type,
            "estimated_latency_ms": sub_info["latency_base_ms"],
            "efficiency_gflops_per_watt": sub_info["efficiency_gflops_per_watt"],
            "energy_cost": round(energy_cost, 4),
            "substrate_health": sub_info["health"],
            "execution_time_ms": round((time.time() - start_time) * 1000.0, 3),
            "timestamp": time.time(),
        }

        # Update load after completion
        sub_info["current_load"] = max(0, sub_info["current_load"] - 1)

        self.dispatch_history.append(dispatch_record)
        return dispatch_record

    def process_queue(self, max_tasks: int = 10) -> list[dict[str, Any]]:
        """Process tasks from the priority queue."""
        results: list[dict[str, Any]] = []
        for task_record in self._task_queue[:max_tasks]:
            result = self.execute_substrate_task(task_record["task"])
            task_record["status"] = "completed"
            task_record["result"] = result
            results.append(result)
        # Remove completed tasks from queue
        self._task_queue = [t for t in self._task_queue if t["status"] == "queued"]
        return results

    # ------------------------------------------------------------------
    # Failover
    # ------------------------------------------------------------------

    def execute_with_failover(
        self, task: dict[str, Any], max_retries: int = 3
    ) -> dict[str, Any]:
        """Execute task with automatic failover on substrate failure."""
        for attempt in range(max_retries):
            result = self.execute_substrate_task(task)
            # Check if substrate was healthy during execution
            substrate = self.substrates.get(result["selected_substrate"])
            if substrate and substrate["health"] > 0.5:
                result["attempts"] = attempt + 1
                return result
            # Failover: deactivate failed substrate and retry
            self._substrate_failover_count[result["selected_substrate"]] += 1
            self.set_substrate_active(result["selected_substrate"], False)

        # All attempts failed
        return {
            "task_id": task.get("id", "unknown"),
            "success": False,
            "error": "All substrate attempts failed",
            "attempts": max_retries,
        }

    # ------------------------------------------------------------------
    # Energy accounting
    # ------------------------------------------------------------------

    def get_energy_report(self) -> dict[str, Any]:
        """Return total energy costs per substrate."""
        total_energy = sum(self._energy_account.values())
        return {
            "total_energy_cost": round(total_energy, 4),
            "per_substrate": dict(self._energy_account),
            "energy_efficiency_ranking": sorted(
                self.substrates.keys(),
                key=lambda s: self.substrates[s].get("efficiency_gflops_per_watt", 0),
                reverse=True,
            ),
        }

    # ------------------------------------------------------------------
    # Benchmarking
    # ------------------------------------------------------------------

    def benchmark_substrates(
        self, test_task: dict[str, Any] = {}, trials: int = 5
    ) -> dict[str, dict[str, Any]]:
        """Run simple benchmark across all active substrates."""
        results: dict[str, dict[str, Any]] = {}
        for stype, sub_info in self.substrates.items():
            if not sub_info["active"]:
                continue
            latencies: list[float] = []
            for _ in range(trials):
                start = time.time()
                result = self.execute_substrate_task(
                    test_task or {"id": "bench", "category": "general"}
                )
                latencies.append(result["execution_time_ms"])

            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            results[stype] = {
                "avg_latency_ms": round(avg_latency, 3),
                "min_latency_ms": round(min(latencies), 3) if latencies else 0,
                "max_latency_ms": round(max(latencies), 3) if latencies else 0,
                "efficiency": sub_info["efficiency_gflops_per_watt"],
                "health": sub_info["health"],
            }
        return results

    # ------------------------------------------------------------------
    # Load balancing
    # ------------------------------------------------------------------

    def rebalance_loads(self) -> dict[str, int]:
        """Redistribute queued tasks across substrates for balanced load."""
        active = [s for s in self.substrates.values() if s["active"]]
        if not active or not self._task_queue:
            return {}

        # Sort substrates by available capacity
        active.sort(key=lambda s: s["capacity"] - s["current_load"], reverse=True)

        assignments: dict[str, int] = defaultdict(int)
        for i, task_record in enumerate(self._task_queue):
            # Assign to substrate with most available capacity
            substrate = active[i % len(active)]
            substrate["current_load"] += 1
            task_record["task"]["preferred_type"] = substrate["type"]
            assignments[substrate["type"]] += 1

        return dict(assignments)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return statistics dict."""
        return {
            "registered_substrates": len(self.substrates),
            "active_substrates": sum(
                1 for s in self.substrates.values() if s["active"]
            ),
            "total_dispatches": len(self.dispatch_history),
            "queued_tasks": len(self._task_queue),
            "substrate_counts": {
                st: sum(
                    1 for d in self.dispatch_history if d["selected_substrate"] == st
                )
                for st in self.substrates
            },
            "total_energy_cost": round(sum(self._energy_account.values()), 4),
            "failover_events": dict(self._substrate_failover_count),
        }
