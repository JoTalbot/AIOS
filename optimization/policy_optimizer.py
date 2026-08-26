from dataclasses import dataclass


@dataclass
class OptimizationResult:
    action: str
    previous_score: float
    optimized_score: float


class PolicyOptimizer:
    """
    Connects optimization metrics with adaptive policy decisions.
    """

    def optimize(self, action: str, score: float) -> OptimizationResult:
        improved = min(1.0, score + 0.05)

        return OptimizationResult(
            action=action,
            previous_score=score,
            optimized_score=improved,
        )
