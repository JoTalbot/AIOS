"""A/B testing engine — compare scraping strategies and measure performance.

Provides:
- Experiment creation with variants (Strategy A vs Strategy B)
- Metric collection (success rate, latency, items collected, cost)
- Statistical significance testing (Chi-square for proportions, t-test for means)
- Automatic winner selection with confidence thresholds
- Experiment lifecycle: draft → running → completed → analyzed

Pure Python — no external stats libraries required.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExperimentStatus(Enum):
    """Lifecycle status of an A/B experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ANALYZED = "analyzed"
    CANCELLED = "cancelled"


class MetricType(Enum):
    """Types of metrics tracked in experiments."""

    RATE = "rate"  # Proportion (success rate, conversion rate)
    MEAN = "mean"  # Average (latency, items collected)
    COUNT = "count"  # Total count (items, errors)
    PERCENTILE = "percentile"  # P50, P90, P99


@dataclass
class Variant:
    """A variant (strategy) in an A/B experiment."""

    name: str  # e.g. "strategy_a", "baseline"
    description: str = ""  # Human-readable description
    config: dict[str, Any] = field(default_factory=dict)  # Strategy configuration
    observations: list[float] = field(default_factory=list)  # Raw metric observations
    rate_successes: int = 0  # For rate metrics: successes
    rate_total: int = 0  # For rate metrics: total trials
    start_time: float | None = None
    end_time: float | None = None

    @property
    def sample_size(self) -> int:
        """Number of observations collected."""
        if self.rate_total > 0:
            return self.rate_total
        return len(self.observations)

    @property
    def mean(self) -> float:
        """Mean of observations."""
        if not self.observations:
            return 0.0
        return sum(self.observations) / len(self.observations)

    @property
    def variance(self) -> float:
        """Variance of observations."""
        if len(self.observations) < 2:
            return 0.0
        m = self.mean
        return sum((x - m) ** 2 for x in self.observations) / (
            len(self.observations) - 1
        )

    @property
    def std_dev(self) -> float:
        """Standard deviation."""
        return math.sqrt(self.variance)

    @property
    def rate(self) -> float:
        """Success rate (successes / total)."""
        if self.rate_total == 0:
            return 0.0
        return self.rate_successes / self.rate_total

    def add_observation(self, value: float) -> None:
        """Add a metric observation (for mean/count metrics).

        Args:
            value: Observed metric value.
        """
        self.observations.append(value)

    def add_rate_observation(self, success: bool) -> None:
        """Add a rate metric observation (success/failure).

        Args:
            success: Whether this trial succeeded.
        """
        self.rate_total += 1
        if success:
            self.rate_successes += 1


@dataclass
class ExperimentResult:
    """Result of analyzing an A/B experiment."""

    experiment_id: str
    winner: str | None  # Name of winning variant
    confidence: float  # Statistical confidence (0.0 to 1.0)
    is_significant: bool  # Whether difference is statistically significant
    metric_type: MetricType
    variant_a_name: str
    variant_a_value: float  # Mean or rate for variant A
    variant_b_name: str
    variant_b_value: float  # Mean or rate for variant B
    lift: float  # Relative improvement (B vs A)
    p_value: float  # Statistical p-value
    sample_size_a: int
    sample_size_b: int
    recommendation: str = ""  # Human-readable recommendation


class ABTestingEngine:
    """A/B testing engine for comparing scraping strategies.

    Provides:
    - create_experiment() — define experiment with 2+ variants
    - record_observation() — add metric data for a variant
    - analyze() — run statistical significance test
    - analyze_all() — analyze all running experiments
    - auto_complete() — stop experiment when significance reached
    """

    def __init__(
        self,
        min_sample_size: int = 30,
        significance_threshold: float = 0.05,
        confidence_threshold: float = 0.95,
    ) -> None:
        """Initialize ABTestingEngine.

        Args:
            min_sample_size: Minimum observations per variant before analysis.
            significance_threshold: p-value threshold for significance (default 0.05).
            confidence_threshold: Minimum confidence to declare winner.
        """
        self.min_sample_size = min_sample_size
        self.significance_threshold = significance_threshold
        self.confidence_threshold = confidence_threshold
        self._experiments: dict[str, Experiment] = {}
        self._counter: int = 0

    def _next_id(self) -> str:
        """Generate unique experiment ID."""
        self._counter += 1
        return f"exp_{self._counter}"

    def create_experiment(
        self,
        name: str,
        metric_type: MetricType = MetricType.MEAN,
        variants: list[dict[str, Any]] | None = None,
        description: str = "",
        min_sample_size: int | None = None,
    ) -> Experiment:
        """Create a new A/B experiment.

        Args:
            name: Experiment name.
            metric_type: Type of metric to track.
            variants: List of variant configs [{name, description, config}].
            description: Experiment description.
            min_sample_size: Override minimum sample size.

        Returns:
            Experiment instance.
        """
        exp_id = self._next_id()
        min_size = min_sample_size or self.min_sample_size

        variant_objs = []
        if variants:
            for v in variants:
                variant_objs.append(
                    Variant(
                        name=v.get("name", f"variant_{len(variant_objs)}"),
                        description=v.get("description", ""),
                        config=v.get("config", {}),
                    )
                )

        # If only one variant provided, add a default "baseline"
        if len(variant_objs) == 1:
            variant_objs.insert(
                0, Variant(name="baseline", description="Default strategy")
            )

        # If no variants, create default A/B pair
        if not variant_objs:
            variant_objs = [
                Variant(name="variant_a", description="Strategy A"),
                Variant(name="variant_b", description="Strategy B"),
            ]

        exp = Experiment(
            experiment_id=exp_id,
            name=name,
            metric_type=metric_type,
            variants=variant_objs,
            description=description,
            min_sample_size=min_size,
        )

        self._experiments[exp_id] = exp
        return exp

    def start_experiment(self, experiment_id: str) -> Experiment | None:
        """Start a draft experiment.

        Args:
            experiment_id: Experiment to start.

        Returns:
            Updated Experiment or None if not found.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        if exp.status != ExperimentStatus.DRAFT:
            return exp
        exp.status = ExperimentStatus.RUNNING
        exp.started_at = time.time()
        for v in exp.variants:
            v.start_time = time.time()
        return exp

    def pause_experiment(self, experiment_id: str) -> Experiment | None:
        """Pause a running experiment.

        Args:
            experiment_id: Experiment to pause.

        Returns:
            Updated Experiment or None.
        """
        exp = self._experiments.get(experiment_id)
        if exp and exp.status == ExperimentStatus.RUNNING:
            exp.status = ExperimentStatus.PAUSED
            return exp
        return exp

    def record_observation(
        self,
        experiment_id: str,
        variant_name: str,
        value: float,
    ) -> None:
        """Record a metric observation for a variant.

        Args:
            experiment_id: Target experiment.
            variant_name: Which variant to record for.
            value: Observed metric value.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status not in (
            ExperimentStatus.RUNNING,
            ExperimentStatus.PAUSED,
        ):
            return

        for v in exp.variants:
            if v.name == variant_name:
                if exp.metric_type == MetricType.RATE:
                    v.add_rate_observation(value >= 1.0)
                else:
                    v.add_observation(value)
                break

    def record_rate_observation(
        self,
        experiment_id: str,
        variant_name: str,
        success: bool,
    ) -> None:
        """Record a success/failure observation for rate metrics.

        Args:
            experiment_id: Target experiment.
            variant_name: Which variant.
            success: True if this trial succeeded.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status not in (
            ExperimentStatus.RUNNING,
            ExperimentStatus.PAUSED,
        ):
            return

        for v in exp.variants:
            if v.name == variant_name:
                v.add_rate_observation(success)
                break

    def _chi_square_test(self, a: Variant, b: Variant) -> tuple[float, float]:
        """Chi-square test for comparing two proportions (rate metrics).

        Args:
            a: Variant A.
            b: Variant B.

        Returns:
            (chi_square_statistic, p_value).
        """
        s_a = a.rate_successes
        f_a = a.rate_total - a.rate_successes
        s_b = b.rate_successes
        f_b = b.rate_total - b.rate_successes

        total = s_a + f_a + s_b + f_b
        if total == 0:
            return (0.0, 1.0)

        # Expected values
        p_combined = (s_a + s_b) / total
        e_sa = a.rate_total * p_combined
        e_fa = a.rate_total * (1 - p_combined)
        e_sb = b.rate_total * p_combined
        e_fb = b.rate_total * (1 - p_combined)

        # Chi-square
        chi2 = 0.0
        for obs, exp in [(s_a, e_sa), (f_a, e_fa), (s_b, e_sb), (f_b, e_fb)]:
            if exp > 0:
                chi2 += (obs - exp) ** 2 / exp

        # p-value from chi-square distribution (1 degree of freedom)
        # Using approximation: p = exp(-chi2/2) for small chi2
        # More accurate: use the incomplete gamma function approximation
        p_value = self._chi2_p_value(chi2, df=1)

        return (chi2, p_value)

    def _chi2_p_value(self, chi2: float, df: int = 1) -> float:
        """Approximate p-value from chi-square statistic.

        Args:
            chi2: Chi-square statistic.
            df: Degrees of freedom.

        Returns:
            Approximate p-value.
        """
        # For df=1: use simple approximation
        # p ≈ exp(-chi2/2) for small chi2
        # Better: use series expansion
        if df == 1:
            # P(X > chi2) for chi-square with 1 df
            # = 2 * (1 - Φ(√chi2)) where Φ is standard normal CDF
            z = math.sqrt(chi2)
            p = 2 * (1 - self._normal_cdf(z))
            return min(1.0, p)

        # General approximation for other df
        x = chi2 / 2
        k = df / 2
        # Approximate using Poisson-like terms
        p = 0.0
        for i in range(int(k), 50):
            term = math.exp(-x) * (x**i) / math.factorial(i) if i < 20 else 0
            p += term
        return min(1.0, max(0.0, 1 - p))

    def _normal_cdf(self, z: float) -> float:
        """Approximate standard normal CDF.

        Args:
            z: Standard normal z-score.

        Returns:
            CDF value (0.0 to 1.0).
        """
        # Using approximation from Abramowitz & Stegun
        if z < 0:
            return 1 - self._normal_cdf(-z)

        b0 = 0.2316419
        b1 = 0.3193815
        b2 = -0.3565638
        b3 = 1.7814779
        b4 = -1.8212560
        b5 = 1.3302744

        t = 1 / (1 + b0 * z)
        t2 = t * t
        t3 = t2 * t
        t4 = t3 * t
        t5 = t4 * t

        pdf = math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
        cdf = 1 - pdf * (b1 * t + b2 * t2 + b3 * t3 + b4 * t4 + b5 * t5)

        return cdf

    def _t_test(self, a: Variant, b: Variant) -> tuple[float, float]:
        """Two-sample t-test for comparing means.

        Args:
            a: Variant A.
            b: Variant B.

        Returns:
            (t_statistic, p_value).
        """
        n_a = len(a.observations)
        n_b = len(b.observations)

        if n_a < 2 or n_b < 2:
            return (0.0, 1.0)

        mean_a = a.mean
        mean_b = b.mean
        var_a = a.variance
        var_b = b.variance

        # Welch's t-test (handles unequal variances)
        se_a = var_a / n_a
        se_b = var_b / n_b
        se_diff = math.sqrt(se_a + se_b)

        if se_diff == 0:
            return (0.0, 1.0)

        t_stat = (mean_b - mean_a) / se_diff

        # Degrees of freedom (Welch-Satterthwaite)
        df_num = (se_a + se_b) ** 2
        df_den = se_a**2 / (n_a - 1) + se_b**2 / (n_b - 1)
        if df_den == 0:
            n_a + n_b - 2
        else:
            df_num / df_den

        # p-value from t-distribution approximation
        p_value = 2 * (1 - self._normal_cdf(abs(t_stat)))

        return (t_stat, p_value)

    def analyze(self, experiment_id: str) -> ExperimentResult | None:
        """Analyze an experiment and determine the winner.

        Args:
            experiment_id: Experiment to analyze.

        Returns:
            ExperimentResult with statistical analysis, or None.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or len(exp.variants) < 2:
            return None

        a = exp.variants[0]
        b = exp.variants[1]

        # Check minimum sample size
        if a.sample_size < exp.min_sample_size or b.sample_size < exp.min_sample_size:
            return ExperimentResult(
                experiment_id=experiment_id,
                winner=None,
                confidence=0.0,
                is_significant=False,
                metric_type=exp.metric_type,
                variant_a_name=a.name,
                variant_a_value=a.mean
                if exp.metric_type != MetricType.RATE
                else a.rate,
                variant_b_name=b.name,
                variant_b_value=b.mean
                if exp.metric_type != MetricType.RATE
                else b.rate,
                lift=0.0,
                p_value=1.0,
                sample_size_a=a.sample_size,
                sample_size_b=b.sample_size,
                recommendation="Insufficient sample size — continue experiment",
            )

        # Run statistical test
        if exp.metric_type == MetricType.RATE:
            stat, p_value = self._chi_square_test(a, b)
            val_a = a.rate
            val_b = b.rate
        else:
            _stat, p_value = self._t_test(a, b)
            val_a = a.mean
            val_b = b.mean

        # Determine significance
        is_significant = p_value < self.significance_threshold
        confidence = 1 - p_value

        # Determine winner
        winner = None
        if is_significant and confidence >= self.confidence_threshold:
            if val_b > val_a:
                winner = b.name
            elif val_a > val_b:
                winner = a.name

        # Compute lift
        lift = (val_b - val_a) / val_a if val_a > 0 else 0.0

        # Recommendation
        if is_significant:
            if winner:
                rec = f"Winner: {winner} with {confidence:.1%} confidence (lift: {lift:.1%})"
            else:
                rec = f"No clear winner — both variants perform similarly (p={p_value:.4f})"
        else:
            rec = f"Not statistically significant (p={p_value:.4f}) — continue collecting data"

        result = ExperimentResult(
            experiment_id=experiment_id,
            winner=winner,
            confidence=round(confidence, 4),
            is_significant=is_significant,
            metric_type=exp.metric_type,
            variant_a_name=a.name,
            variant_a_value=round(val_a, 4),
            variant_b_name=b.name,
            variant_b_value=round(val_b, 4),
            lift=round(lift, 4),
            p_value=round(p_value, 4),
            sample_size_a=a.sample_size,
            sample_size_b=b.sample_size,
            recommendation=rec,
        )

        # Update experiment status
        if is_significant and winner:
            exp.status = ExperimentStatus.ANALYZED
            exp.completed_at = time.time()
            for v in exp.variants:
                v.end_time = time.time()

        return result

    def analyze_all(self) -> list[ExperimentResult]:
        """Analyze all running experiments.

        Returns:
            List of ExperimentResult for all experiments.
        """
        results = []
        for exp_id, exp in self._experiments.items():
            if exp.status in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
                r = self.analyze(exp_id)
                if r:
                    results.append(r)
        return results

    def auto_complete(self, experiment_id: str) -> Experiment | None:
        """Auto-complete experiment if significance threshold reached.

        Args:
            experiment_id: Experiment to check.

        Returns:
            Completed Experiment or None.
        """
        result = self.analyze(experiment_id)
        if result and result.is_significant and result.winner:
            exp = self._experiments.get(experiment_id)
            if exp:
                exp.status = ExperimentStatus.COMPLETED
                exp.completed_at = time.time()
                exp.result = result
                return exp
        return None

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        """Get experiment by ID.

        Args:
            experiment_id: Experiment ID.

        Returns:
            Experiment instance or None.
        """
        return self._experiments.get(experiment_id)

    def list_experiments(
        self, status: ExperimentStatus | None = None
    ) -> list[Experiment]:
        """List experiments, optionally filtered by status.

        Args:
            status: Filter by status (None = all).

        Returns:
            List of Experiment instances.
        """
        if status:
            return [e for e in self._experiments.values() if e.status == status]
        return list(self._experiments.values())

    def cancel_experiment(self, experiment_id: str) -> Experiment | None:
        """Cancel an experiment.

        Args:
            experiment_id: Experiment to cancel.

        Returns:
            Cancelled Experiment or None.
        """
        exp = self._experiments.get(experiment_id)
        if exp and exp.status in (
            ExperimentStatus.DRAFT,
            ExperimentStatus.RUNNING,
            ExperimentStatus.PAUSED,
        ):
            exp.status = ExperimentStatus.CANCELLED
            return exp
        return None


@dataclass
class Experiment:
    """An A/B experiment with variants and metrics."""

    experiment_id: str
    name: str
    metric_type: MetricType = MetricType.MEAN
    variants: list[Variant] = field(default_factory=list)
    description: str = ""
    status: ExperimentStatus = ExperimentStatus.DRAFT
    min_sample_size: int = 30
    started_at: float | None = None
    completed_at: float | None = None
    result: ExperimentResult | None = None

    @property
    def duration(self) -> float | None:
        """Experiment duration in seconds."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return time.time() - self.started_at
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize experiment to dict."""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "metric_type": self.metric_type.value,
            "variants": [
                {
                    "name": v.name,
                    "description": v.description,
                    "sample_size": v.sample_size,
                    "mean": round(v.mean, 4),
                    "rate": round(v.rate, 4),
                    "std_dev": round(v.std_dev, 4),
                }
                for v in self.variants
            ],
            "status": self.status.value,
            "min_sample_size": self.min_sample_size,
            "duration": round(self.duration or 0, 2),
        }
