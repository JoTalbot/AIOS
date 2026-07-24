"""Auto-tuning engine — dynamic optimization of scraping parameters.

Provides:
- Parameter registry (configurable scraping params with ranges)
- Performance feedback loop (success rate → param adjustment)
- Grid search (exhaustive parameter space exploration)
- Bayesian-style optimization (best-first with exploration)
- Hill climbing (local optimization around current best)
- Adaptive threshold adjustment

Pure Python — no external optimization libraries required.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ParamType(Enum):
    """Parameter value types."""

    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    CHOICE = "choice"  # Enum-like: discrete set of options


class TuningStrategy(Enum):
    """Parameter tuning strategies."""

    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    HILL_CLIMBING = "hill_climbing"
    ADAPTIVE = "adaptive"  # Bayesian-style exploration


@dataclass
class TunableParam:
    """A tunable scraping parameter with range and current value."""

    name: str
    param_type: ParamType
    min_value: float | None = None  # For INT/FLOAT
    max_value: float | None = None  # For INT/FLOAT
    step: float | None = None  # Step size for grid search
    choices: list[str] | None = None  # For CHOICE type
    default: float | str | bool = 0
    current: float | str | bool | None = None
    best: float | str | bool | None = None
    description: str = ""

    def __post_init__(self) -> None:
        """Set current and best to default if not specified."""
        if self.current is None:
            self.current = self.default
        if self.best is None:
            self.best = self.default

    def random_value(self) -> float | str | bool:
        """Generate a random value within the parameter range.

        Returns:
            Random parameter value.
        """
        if self.param_type == ParamType.BOOL:
            return random.choice([True, False])
        elif self.param_type == ParamType.CHOICE:
            return random.choice(self.choices or ["default"])
        elif self.param_type == ParamType.INT:
            min_v = int(self.min_value or 0)
            max_v = int(self.max_value or 100)
            return random.randint(min_v, max_v)
        else:  # FLOAT
            min_v = self.min_value or 0.0
            max_v = self.max_value or 1.0
            return random.uniform(min_v, max_v)

    def grid_values(self) -> list[float | str | bool]:
        """Generate all values for grid search.

        Returns:
            List of parameter values to test.
        """
        if self.param_type == ParamType.BOOL:
            return [True, False]
        elif self.param_type == ParamType.CHOICE:
            return list(self.choices or ["default"])
        elif self.param_type == ParamType.INT:
            min_v = int(self.min_value or 0)
            max_v = int(self.max_value or 100)
            step = int(self.step or 1)
            return list(range(min_v, max_v + 1, step))
        else:  # FLOAT
            min_v = self.min_value or 0.0
            max_v = self.max_value or 1.0
            step = self.step or 0.1
            values = []
            v = min_v
            while v <= max_v:
                values.append(round(v, 4))
                v += step
            return values

    def clamp(self, value: float) -> float:
        """Clamp value to parameter range.

        Args:
            value: Value to clamp.

        Returns:
            Clamped value.
        """
        if self.param_type in (ParamType.BOOL, ParamType.CHOICE):
            return value
        min_v = self.min_value or float("-inf")
        max_v = self.max_value or float("inf")
        return max(min_v, min(max_v, value))


@dataclass
class TuningResult:
    """Result of a tuning session."""

    strategy: TuningStrategy
    params: dict[str, Any]  # Best parameter configuration found
    score: float  # Best score achieved
    iterations: int  # Number of configurations tested
    improvement_pct: float  # Improvement over default
    duration: float  # Time spent tuning (seconds)
    history: list[tuple[dict[str, Any], float]] = field(default_factory=list)


@dataclass
class PerformanceFeedback:
    """Performance feedback from a scraping session."""

    params: dict[str, Any]  # Parameters used in this session
    success_rate: float  # 0.0 to 1.0
    latency_ms: float  # Average response latency
    items_collected: int  # Number of items scraped
    errors: int  # Number of errors
    cost: float = 0.0  # Optional cost metric
    timestamp: float = field(default_factory=time.time)


class AutoTuningEngine:
    """Auto-tuning engine for scraping parameter optimization.

    Provides:
    - register_param() — define tunable parameters
    - record_feedback() — collect performance feedback
    - tune() — run optimization using selected strategy
    - tune_grid() — exhaustive grid search
    - tune_random() — random parameter sampling
    - tune_hill_climbing() — local optimization
    - tune_adaptive() — Bayesian-style best-first exploration
    - get_best_params() — retrieve current best configuration
    """

    def __init__(
        self,
        scoring_fn: Any | None = None,
        default_strategy: TuningStrategy = TuningStrategy.ADAPTIVE,
        max_iterations: int = 50,
    ) -> None:
        """Initialize AutoTuningEngine.

        Args:
            scoring_fn: Function(params_dict) → score. Default: use feedback data.
            default_strategy: Default tuning strategy.
            max_iterations: Maximum iterations for tuning.
        """
        self.scoring_fn = scoring_fn
        self.default_strategy = default_strategy
        self.max_iterations = max_iterations
        self._params: dict[str, TunableParam] = {}
        self._feedback: list[PerformanceFeedback] = []
        self._best_score: float = 0.0
        self._best_params: dict[str, Any] = {}
        self._default_score: float = 0.0
        self._tuning_history: list[tuple[dict[str, Any], float]] = []

    def register_param(self, param: TunableParam) -> None:
        """Register a tunable parameter.

        Args:
            param: TunableParam to register.
        """
        self._params[param.name] = param
        self._best_params[param.name] = param.best

    def register_params(self, params: list[TunableParam]) -> None:
        """Register multiple tunable parameters.

        Args:
            params: List of TunableParam instances.
        """
        for p in params:
            self.register_param(p)

    def record_feedback(self, feedback: PerformanceFeedback) -> None:
        """Record performance feedback from a scraping session.

        Args:
            feedback: PerformanceFeedback instance.
        """
        self._feedback.append(feedback)

        # Update current params
        for name, value in feedback.params.items():
            if name in self._params:
                self._params[name].current = value

        # Compute score
        score = self._compute_score(feedback)

        # Update best if improved
        if score > self._best_score:
            self._best_score = score
            self._best_params = dict(feedback.params)
            for name, value in feedback.params.items():
                if name in self._params:
                    self._params[name].best = value

        # Record default score if first feedback
        if not self._default_score and all(
            feedback.params.get(name) == self._params[name].default
            for name in self._params
        ):
            self._default_score = score

    def _compute_score(self, feedback: PerformanceFeedback) -> float:
        """Compute score from performance feedback.

        Score = success_rate * 0.5 + (1 - normalized_latency) * 0.2 + items_weight * 0.3

        Args:
            feedback: PerformanceFeedback.

        Returns:
            Computed score (0.0 to 1.0).
        """
        if self.scoring_fn:
            return self.scoring_fn(feedback.params)

        # Default scoring: weighted combination
        success = feedback.success_rate
        # Normalize latency: 0ms = 1.0, 5000ms = 0.0
        latency_score = max(0.0, 1.0 - feedback.latency_ms / 5000.0)
        # Normalize items: 0 = 0.0, 100 = 1.0
        items_score = min(1.0, feedback.items_collected / 100.0)
        # Error penalty
        error_penalty = min(1.0, feedback.errors / 10.0)

        score = (
            success * 0.5
            + latency_score * 0.2
            + items_score * 0.3
            - error_penalty * 0.1
        )
        return max(0.0, min(1.0, score))

    def get_current_params(self) -> dict[str, Any]:
        """Get current parameter values.

        Returns:
            Dict of param_name → current_value.
        """
        return {name: p.current for name, p in self._params.items()}

    def get_best_params(self) -> dict[str, Any]:
        """Get best parameter values found so far.

        Returns:
            Dict of param_name → best_value.
        """
        return dict(self._best_params)

    def get_default_params(self) -> dict[str, Any]:
        """Get default parameter values.

        Returns:
            Dict of param_name → default_value.
        """
        return {name: p.default for name, p in self._params.items()}

    def _generate_config(self, strategy: TuningStrategy) -> dict[str, Any]:
        """Generate next parameter configuration to test.

        Args:
            strategy: Tuning strategy to use.

        Returns:
            Dict of param_name → value.
        """
        config = {}
        for name, param in self._params.items():
            if strategy == TuningStrategy.RANDOM_SEARCH:
                config[name] = param.random_value()
            elif strategy == TuningStrategy.HILL_CLIMBING:
                # Perturb best value
                best = param.best if param.best is not None else param.default
                if param.param_type in (ParamType.INT, ParamType.FLOAT):
                    perturbation = (
                        (param.max_value - param.min_value) * 0.1
                        if param.max_value and param.min_value
                        else 1.0
                    )
                    config[name] = param.clamp(
                        best + random.uniform(-perturbation, perturbation)
                    )
                    if param.param_type == ParamType.INT:
                        config[name] = int(config[name])
                elif param.param_type == ParamType.BOOL:
                    config[name] = not best if random.random() < 0.3 else best
                else:
                    config[name] = param.random_value()
            elif strategy == TuningStrategy.ADAPTIVE:
                # 70% explore around best, 30% random
                if random.random() < 0.7:
                    config[name] = self._adaptive_perturb(param)
                else:
                    config[name] = param.random_value()
        return config

    def _adaptive_perturb(self, param: TunableParam) -> float | str | bool:
        """Perturb parameter for adaptive tuning.

        Args:
            param: TunableParam to perturb.

        Returns:
            Perturbed value.
        """
        best = param.best if param.best is not None else param.default
        if param.param_type in (ParamType.INT, ParamType.FLOAT):
            range_size = (
                (param.max_value - param.min_value)
                if param.max_value and param.min_value
                else 10.0
            )
            # Decreasing perturbation as we get closer to best
            perturbation = range_size * 0.2 * random.uniform(-1, 1)
            return param.clamp(float(best) + perturbation)
        elif param.param_type == ParamType.BOOL:
            return not best if random.random() < 0.2 else best
        else:
            return param.random_value()

    def tune(
        self,
        strategy: TuningStrategy | None = None,
        max_iterations: int | None = None,
        scoring_fn: Any | None = None,
    ) -> TuningResult:
        """Run parameter tuning.

        Args:
            strategy: Tuning strategy override.
            max_iterations: Override max iterations.
            scoring_fn: Override scoring function.

        Returns:
            TuningResult with best configuration found.
        """
        effective_strategy = strategy or self.default_strategy
        effective_max = max_iterations or self.max_iterations
        effective_scoring = scoring_fn or self.scoring_fn or self._default_scoring

        start_time = time.time()
        history: list[tuple[dict[str, Any], float]] = []

        if effective_strategy == TuningStrategy.GRID_SEARCH:
            return self.tune_grid(scoring_fn=effective_scoring)

        best_config = (
            dict(self._best_params) if self._best_params else self.get_default_params()
        )
        best_score = self._best_score if self._best_score else 0.0

        for i in range(effective_max):
            config = self._generate_config(effective_strategy)

            # Evaluate
            score = effective_scoring(config)
            history.append((dict(config), score))

            if score > best_score:
                best_score = score
                best_config = dict(config)
                # Update param best values
                for name, value in config.items():
                    if name in self._params:
                        self._params[name].best = value

        # Compute improvement
        default_score = self._default_score if self._default_score > 0 else 0.1
        improvement = (
            ((best_score - default_score) / default_score * 100)
            if default_score > 0
            else 0.0
        )

        duration = time.time() - start_time

        result = TuningResult(
            strategy=effective_strategy,
            params=best_config,
            score=round(best_score, 4),
            iterations=len(history),
            improvement_pct=round(improvement, 2),
            duration=round(duration, 2),
            history=history,
        )

        self._tuning_history.extend(history)
        self._best_score = best_score
        self._best_params = best_config

        return result

    def _default_scoring(self, config: dict[str, Any]) -> float:
        """Default scoring function using recorded feedback.

        Args:
            config: Parameter configuration to score.

        Returns:
            Estimated score (0.0 to 1.0).
        """
        if self._feedback:
            # Find closest feedback by params similarity
            best_match = 0.0
            for fb in self._feedback:
                similarity = self._params_similarity(config, fb.params)
                score = self._compute_score(fb)
                weighted = similarity * score
                best_match = max(best_match, weighted)
            return best_match

        # No feedback — use heuristic based on params values
        score = 0.5
        for name, value in config.items():
            param = self._params.get(name)
            if not param:
                continue
            if param.param_type in (ParamType.INT, ParamType.FLOAT):
                # Prefer middle of range
                if param.max_value and param.min_value:
                    mid = (param.max_value + param.min_value) / 2
                    range_size = param.max_value - param.min_value
                    if range_size > 0:
                        closeness = 1 - abs(float(value) - mid) / range_size
                        score *= 0.8 + closeness * 0.2
        return score

    def _params_similarity(self, a: dict[str, Any], b: dict[str, Any]) -> float:
        """Compute similarity between two parameter configurations.

        Args:
            a: First config.
            b: Second config.

        Returns:
            Similarity score (0.0 to 1.0).
        """
        matches = 0
        total = len(self._params)
        if total == 0:
            return 0.0

        for name in self._params:
            val_a = a.get(name)
            val_b = b.get(name)
            param = self._params[name]

            if val_a == val_b:
                matches += 1
            elif param.param_type in (ParamType.INT, ParamType.FLOAT):
                # Proximity match for numeric params
                if param.max_value and param.min_value:
                    range_size = param.max_value - param.min_value
                    if range_size > 0:
                        proximity = (
                            1 - abs(float(val_a or 0) - float(val_b or 0)) / range_size
                        )
                        matches += proximity
            # Choice/bool: exact match only

        return matches / total

    def tune_grid(self, scoring_fn: Any | None = None) -> TuningResult:
        """Exhaustive grid search over parameter space.

        Args:
            scoring_fn: Override scoring function.

        Returns:
            TuningResult from grid search.
        """
        effective_scoring = scoring_fn or self.scoring_fn or self._default_scoring
        start_time = time.time()

        # Generate grid for each param
        param_grids = {}
        for name, param in self._params.items():
            param_grids[name] = param.grid_values()

        # Generate all combinations (limited by max_iterations)
        configs = self._grid_combinations(param_grids)
        configs = configs[: self.max_iterations]

        history: list[tuple[dict[str, Any], float]] = []
        best_config = self.get_default_params()
        best_score = 0.0

        for config in configs:
            score = effective_scoring(config)
            history.append((dict(config), score))
            if score > best_score:
                best_score = score
                best_config = dict(config)

        # Update best params
        for name, value in best_config.items():
            if name in self._params:
                self._params[name].best = value

        default_score = self._default_score if self._default_score > 0 else 0.1
        improvement = (
            ((best_score - default_score) / default_score * 100)
            if default_score > 0
            else 0.0
        )

        return TuningResult(
            strategy=TuningStrategy.GRID_SEARCH,
            params=best_config,
            score=round(best_score, 4),
            iterations=len(history),
            improvement_pct=round(improvement, 2),
            duration=round(time.time() - start_time, 2),
            history=history,
        )

    def _grid_combinations(self, param_grids: dict[str, list]) -> list[dict[str, Any]]:
        """Generate all combinations from parameter grids.

        Args:
            param_grids: Dict of param_name → list of values.

        Returns:
            List of configuration dicts.
        """
        if not param_grids:
            return [{}]

        names = list(param_grids.keys())
        values = list(param_grids.values())

        # Generate Cartesian product
        configs = []
        for combo in self._cartesian_product(values):
            config = dict(zip(names, combo))
            configs.append(config)

        return configs

    def _cartesian_product(self, lists: list[list]) -> list[list]:
        """Compute Cartesian product of lists.

        Args:
            lists: List of value lists.

        Returns:
            List of all combinations.
        """
        result = [[]]
        for lst in lists:
            new_result = []
            for prefix in result:
                for item in lst:
                    new_result.append(prefix + [item])
            result = new_result
        return result

    def tune_random(
        self, n_iterations: int = 50, scoring_fn: Any | None = None
    ) -> TuningResult:
        """Random parameter search.

        Args:
            n_iterations: Number of random configurations to test.
            scoring_fn: Override scoring function.

        Returns:
            TuningResult from random search.
        """
        return self.tune(
            strategy=TuningStrategy.RANDOM_SEARCH,
            max_iterations=n_iterations,
            scoring_fn=scoring_fn,
        )

    def tune_hill_climbing(
        self, n_iterations: int = 50, scoring_fn: Any | None = None
    ) -> TuningResult:
        """Hill climbing optimization.

        Args:
            n_iterations: Number of iterations.
            scoring_fn: Override scoring function.

        Returns:
            TuningResult from hill climbing.
        """
        return self.tune(
            strategy=TuningStrategy.HILL_CLIMBING,
            max_iterations=n_iterations,
            scoring_fn=scoring_fn,
        )

    def stats(self) -> dict[str, Any]:
        """Get tuning statistics.

        Returns:
            Dict with params count, feedback count, best score, etc.
        """
        return {
            "params_count": len(self._params),
            "feedback_count": len(self._feedback),
            "best_score": round(self._best_score, 4),
            "default_score": round(self._default_score, 4),
            "improvement_pct": round(
                ((self._best_score - self._default_score) / self._default_score * 100)
                if self._default_score > 0
                else 0.0,
                2,
            ),
            "iterations_run": len(self._tuning_history),
            "best_params": dict(self._best_params),
            "current_params": {name: p.current for name, p in self._params.items()},
        }
