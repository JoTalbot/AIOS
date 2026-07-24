"""Predictive Autonomy Regulator for AIOS Executive Layer.

Forecasts execution failure risk based on historic model scores, step complexity,
resource demand, environment context, and agent history, dynamically scaling autonomy levels.
"""

import time
import math
from typing import Any, Dict, List, Tuple, Optional

from .autonomy_manager import AutonomyLevel


class EnvironmentContextAnalyzer:
    """Analyzes the current environment to adjust risk profiles."""
    
    def __init__(self):
        self.critical_environments = ["production", "prod", "mainnet", "live"]
        self.safe_environments = ["sandbox", "dev", "testnet", "local"]
        
    def get_environment_multiplier(self, env_name: str) -> float:
        """Return a risk multiplier based on environment type."""
        env_name = env_name.lower()
        if any(c in env_name for c in self.critical_environments):
            return 1.5
        if any(s in env_name for s in self.safe_environments):
            return 0.5
        return 1.0


class ResourceImpactPredictor:
    """Predicts if an action will exhaust available system resources."""
    
    def __init__(self):
        self.max_cpu_usage = 80.0  # percentage
        self.max_memory_usage_gb = 64.0
        
    def estimate_impact(self, plan_step: Dict[str, Any]) -> float:
        """Returns a normalized risk score based on predicted resource usage."""
        expected_cpu = plan_step.get("expected_cpu_percent", 0.0)
        expected_mem = plan_step.get("expected_memory_gb", 0.0)
        
        cpu_risk = min(1.0, expected_cpu / self.max_cpu_usage)
        mem_risk = min(1.0, expected_mem / self.max_memory_usage_gb)
        
        # Exponential penalty as it approaches limits
        return (cpu_risk ** 2 + mem_risk ** 2) / 2.0


class AgentHistoryAnalyzer:
    """Tracks and analyzes past agent performance to predict future success."""
    
    def __init__(self):
        self.agent_profiles: Dict[str, Dict[str, Any]] = {}
        
    def update_profile(self, agent_id: str, success: bool, complexity: float):
        if agent_id not in self.agent_profiles:
            self.agent_profiles[agent_id] = {"attempts": 0, "failures": 0, "avg_complexity": 0.0}
            
        prof = self.agent_profiles[agent_id]
        prof["attempts"] += 1
        if not success:
            prof["failures"] += 1
            
        # Moving average of complexity handled
        prof["avg_complexity"] = (prof["avg_complexity"] * 0.9) + (complexity * 0.1)
        
    def get_historical_risk(self, agent_id: str, task_complexity: float) -> float:
        """Compute risk purely from historical success rates and capability limits."""
        if agent_id not in self.agent_profiles:
            return 0.3  # Unknown agent risk
            
        prof = self.agent_profiles[agent_id]
        if prof["attempts"] < 5:
            return 0.3  # Not enough data
            
        failure_rate = prof["failures"] / prof["attempts"]
        
        # If task is much harder than what the agent usually does, increase risk
        complexity_ratio = task_complexity / max(0.1, prof["avg_complexity"])
        overreach_penalty = max(0.0, (complexity_ratio - 1.5) * 0.2)
        
        return min(1.0, failure_rate + overreach_penalty)


class PredictiveAutonomyRegulator:
    """Predictive Autonomy Regulator that dynamically bounds agent execution scope."""

    def __init__(
        self, high_risk_threshold: float = 0.6, critical_risk_threshold: float = 0.85
    ):
        """Initialize PredictiveAutonomyRegulator."""
        self.high_risk_threshold = high_risk_threshold
        self.critical_risk_threshold = critical_risk_threshold
        self.history: List[Dict[str, Any]] = []
        
        # Sub-analyzers
        self.env_analyzer = EnvironmentContextAnalyzer()
        self.resource_predictor = ResourceImpactPredictor()
        self.history_analyzer = AgentHistoryAnalyzer()

    def assess_risk(
        self,
        agent_id: str,
        plan_step: Dict[str, Any],
        agent_history_stats: Optional[Dict[str, float]] = None,
        environment: str = "default"
    ) -> float:
        """Calculate normalized failure risk score [0.0, 1.0]."""
        risk_score = 0.1  # baseline minimal risk

        # Factor 1: Plan step operational risk
        action_type = plan_step.get("action", "").lower()
        if any(
            keyword in action_type
            for keyword in ["delete", "drop", "terminate", "wipe", "force", "sudo"]
        ):
            risk_score += 0.4
        elif any(
            keyword in action_type
            for keyword in ["write", "modify", "deploy", "update", "exec"]
        ):
            risk_score += 0.2

        # Factor 2: Complexity and required capabilities
        complexity = plan_step.get("complexity", 1.0)
        if complexity > 5.0:
            risk_score += 0.15
            
        # Factor 3: Resource impact
        resource_risk = self.resource_predictor.estimate_impact(plan_step)
        risk_score += resource_risk * 0.2

        # Factor 4: Historical error rate of the agent
        # We can use provided stats or our internal analyzer
        if agent_history_stats and "failure_rate" in agent_history_stats:
            failure_rate = agent_history_stats.get("failure_rate", 0.0)
            risk_score += failure_rate * 0.3
        else:
            historical_risk = self.history_analyzer.get_historical_risk(agent_id, complexity)
            risk_score += historical_risk * 0.3
            
        # Apply environment multiplier
        env_multiplier = self.env_analyzer.get_environment_multiplier(environment)
        risk_score *= env_multiplier

        normalized_risk = min(1.0, max(0.0, risk_score))
        return normalized_risk

    def regulate_autonomy(
        self,
        agent_id: str,
        current_level: AutonomyLevel,
        plan_step: Dict[str, Any],
        agent_history_stats: Optional[Dict[str, float]] = None,
        environment: str = "default"
    ) -> Tuple[AutonomyLevel, str]:
        """Dynamically regulate autonomy level based on predicted task risk."""
        risk = self.assess_risk(agent_id, plan_step, agent_history_stats, environment)
        effective_level = current_level
        reason = f"Risk evaluated at {risk:.2f} — autonomy maintained at Level {current_level.value}"

        if risk >= self.critical_risk_threshold:
            # Drop to Level 1 (Human-assisted approval required)
            effective_level = AutonomyLevel.LEVEL_1_ASSISTED
            reason = f"Critical Risk ({risk:.2f} >= {self.critical_risk_threshold}) — downgraded to Level 1 Assisted"

        elif (
            risk >= self.high_risk_threshold
            and current_level.value > AutonomyLevel.LEVEL_2_SUPERVISED.value
        ):
            # Clamp to Level 2 (Supervised Execution)
            effective_level = AutonomyLevel.LEVEL_2_SUPERVISED
            reason = f"High Risk ({risk:.2f} >= {self.high_risk_threshold}) — clamped to Level 2 Supervised"

        self.history.append(
            {
                "agent_id": agent_id,
                "environment": environment,
                "original_level": current_level.value,
                "regulated_level": effective_level.value,
                "risk_score": round(risk, 3),
                "reason": reason,
                "timestamp": time.time(),
            }
        )

        return effective_level, reason

    def record_execution_result(self, agent_id: str, plan_step: Dict[str, Any], success: bool):
        """Record the outcome to improve future predictions."""
        complexity = plan_step.get("complexity", 1.0)
        self.history_analyzer.update_profile(agent_id, success, complexity)

    def stats(self) -> Dict[str, Any]:
        """Summary of predictive regulation decisions."""
        return {
            "total_regulations": len(self.history),
            "clamped_count": sum(
                1 for h in self.history if h["regulated_level"] < h["original_level"]
            ),
            "high_risk_threshold": self.high_risk_threshold,
            "critical_risk_threshold": self.critical_risk_threshold,
            "tracked_agents": len(self.history_analyzer.agent_profiles)
        }
