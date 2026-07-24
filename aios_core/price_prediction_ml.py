"""Price prediction ML — polynomial regression and moving-average forecasting.

Extends AICrossPlatformAdvisor.predict_price() (simple linear) with:
- Polynomial regression (degree 2, 3) for curving price trends
- Moving-average smoothing (simple, weighted, exponential)
- Ensemble predictor that averages multiple models
- Trend detection with confidence intervals

Pure Python — no external ML libraries required.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PredictionModel(Enum):
    """Supported prediction model types."""

    LINEAR = "linear"
    POLYNOMIAL_2 = "polynomial_2"
    POLYNOMIAL_3 = "polynomial_3"
    SMA = "simple_moving_average"
    WMA = "weighted_moving_average"
    EMA = "exponential_moving_average"
    ENSEMBLE = "ensemble"


class TrendDirection(Enum):
    """Price trend direction."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class PricePoint:
    """A single price observation point."""

    day: float       # Day index (0-based or timestamp)
    price: float     # Observed price
    volume: float | None = None  # Optional volume/weight for WMA


@dataclass
class PredictionResult:
    """Result of a price prediction."""

    model: PredictionModel
    fingerprint: str
    current_price: float
    predicted_price: float
    trend: TrendDirection
    confidence: float
    slope: float = 0.0
    curvature: float = 0.0          # Second derivative for polynomial
    history_points: int = 0
    horizon_days: int = 7
    residuals: float = 0.0          # Mean squared error of fit
    metadata: dict[str, Any] = field(default_factory=dict)


def _fit_polynomial(points: list[tuple[float, float]], degree: int) -> list[float]:
    """Fit polynomial regression using least-squares (normal equations).

    Solves: X^T X c = X^T y where X = Vandermonde matrix.

    Args:
        points: List of (x, y) tuples.
        degree: Polynomial degree (1=linear, 2=quadratic, 3=cubic).

    Returns:
        Coefficients [c0, c1, c2, ...] for y = c0 + c1*x + c2*x^2 + ...
    """
    n = len(points)
    if n <= degree:
        return []

    # Build Vandermonde matrix
    X: list[list[float]] = []
    y_vec: list[float] = []
    for xi, yi in points:
        row = [xi ** d for d in range(degree + 1)]
        X.append(row)
        y_vec.append(yi)

    # X^T X
    m = degree + 1
    XtX: list[list[float]] = [[0.0] * m for _ in range(m)]
    for i in range(m):
        for j in range(m):
            XtX[i][j] = sum(X[k][i] * X[k][j] for k in range(n))

    # X^T y
    Xty: list[float] = [0.0] * m
    for i in range(m):
        Xty[i] = sum(X[k][i] * y_vec[k] for k in range(n))

    # Solve via Gaussian elimination
    coeffs = _gauss_solve(XtX, Xty, m)
    return coeffs


def _gauss_solve(A: list[list[float]], b: list[float], n: int) -> list[float]:
    """Solve Ax = b via Gaussian elimination with partial pivoting.

    Args:
        A: n×n matrix.
        b: n-vector.
        n: Matrix size.

    Returns:
        Solution vector x.
    """
    # Augmented matrix
    M = [row[:] + [b[i]] for i, row in enumerate(A)]

    # Forward elimination with partial pivoting
    for col in range(n):
        # Find pivot row
        max_row = col
        max_val = abs(M[col][col])
        for row in range(col + 1, n):
            if abs(M[row][col]) > max_val:
                max_val = abs(M[row][col])
                max_row = row
        # Swap rows
        M[col], M[max_row] = M[max_row], M[col]

        pivot = M[col][col]
        if abs(pivot) < 1e-12:
            return [0.0] * n  # Degenerate

        for row in range(col + 1, n):
            factor = M[row][col] / pivot
            for j in range(col, n + 1):
                M[row][j] -= factor * M[col][j]

    # Back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n]
        for j in range(i + 1, n):
            s -= M[i][j] * x[j]
        if abs(M[i][i]) < 1e-12:
            x[i] = 0.0
        else:
            x[i] = s / M[i][i]

    return x


def _eval_poly(coeffs: list[float], x: float) -> float:
    """Evaluate polynomial at x.

    Args:
        coeffs: Coefficients [c0, c1, c2, ...].
        x: Input value.

    Returns:
        Polynomial value at x.
    """
    return sum(c * x ** i for i, c in enumerate(coeffs))


def _mean_squared_error(
    points: list[tuple[float, float]], coeffs: list[float]
) -> float:
    """Compute MSE of polynomial fit against observed data.

    Args:
        points: Observed (x, y) data.
        coeffs: Polynomial coefficients.

    Returns:
        Mean squared error.
    """
    if not points or not coeffs:
        return float("inf")
    errors = [(yi - _eval_poly(coeffs, xi)) ** 2 for xi, yi in points]
    return sum(errors) / len(errors)


class SimpleMovingAverage:
    """Simple moving average (SMA) price predictor.

    Predicts future price as the mean of the last `window` observations.
    """

    def __init__(self, window: int = 5) -> None:
        """Initialize SMA predictor.

        Args:
            window: Number of recent observations to average.
        """
        self.window = window

    def predict(self, history: list[PricePoint], horizon_days: int = 7) -> PredictionResult:
        """Predict future price using SMA.

        Args:
            history: List of price observations sorted by day.
            horizon_days: Days ahead to predict.

        Returns:
            PredictionResult with SMA prediction.
        """
        if len(history) < self.window:
            # Insufficient data — average all available
            avg = sum(p.price for p in history) / len(history) if history else 0
            return PredictionResult(
                model=PredictionModel.SMA,
                fingerprint="",
                current_price=history[-1].price if history else 0,
                predicted_price=round(avg, 2) if history else 0,
                trend=TrendDirection.STABLE,
                confidence=0.1,
                history_points=len(history),
                horizon_days=horizon_days,
            )

        recent = history[-self.window:]
        avg = sum(p.price for p in recent) / len(recent)
        prices = [p.price for p in history]

        trend = _detect_trend(prices)
        conf = min(0.9, 0.2 + len(history) * 0.05)

        return PredictionResult(
            model=PredictionModel.SMA,
            fingerprint="",
            current_price=history[-1].price,
            predicted_price=round(avg, 2),
            trend=trend,
            confidence=conf,
            history_points=len(history),
            horizon_days=horizon_days,
        )


class WeightedMovingAverage:
    """Weighted moving average (WMA) price predictor.

    Assigns linearly decreasing weights: most recent gets weight `window`,
    second-most gets `window-1`, etc.
    """

    def __init__(self, window: int = 5) -> None:
        """Initialize WMA predictor.

        Args:
            window: Number of recent observations (and max weight).
        """
        self.window = window

    def predict(self, history: list[PricePoint], horizon_days: int = 7) -> PredictionResult:
        """Predict future price using WMA.

        Args:
            history: List of price observations sorted by day.
            horizon_days: Days ahead to predict.

        Returns:
            PredictionResult with WMA prediction.
        """
        if len(history) < self.window:
            recent = history[-len(history):] if history else []
            if not recent:
                return PredictionResult(
                    model=PredictionModel.WMA, fingerprint="",
                    current_price=0, predicted_price=0,
                    trend=TrendDirection.STABLE, confidence=0.1,
                    history_points=0, horizon_days=horizon_days,
                )
            avg = sum(p.price for p in recent) / len(recent)
        else:
            recent = history[-self.window:]
            total_weight = sum(range(1, self.window + 1))
            weighted_sum = sum(
                p.price * (i + 1) for i, p in enumerate(recent)
            )
            avg = weighted_sum / total_weight

        prices = [p.price for p in history]
        trend = _detect_trend(prices)
        conf = min(0.9, 0.25 + len(history) * 0.05)

        return PredictionResult(
            model=PredictionModel.WMA,
            fingerprint="",
            current_price=history[-1].price,
            predicted_price=round(avg, 2),
            trend=trend,
            confidence=conf,
            history_points=len(history),
            horizon_days=horizon_days,
        )


class ExponentialMovingAverage:
    """Exponential moving average (EMA) price predictor.

    Uses smoothing factor α = 2 / (window + 1).
    """

    def __init__(self, window: int = 5) -> None:
        """Initialize EMA predictor.

        Args:
            window: Smoothing window (α = 2/(window+1)).
        """
        self.window = window
        self.alpha = 2.0 / (window + 1)

    def predict(self, history: list[PricePoint], horizon_days: int = 7) -> PredictionResult:
        """Predict future price using EMA.

        Args:
            history: List of price observations sorted by day.
            horizon_days: Days ahead to predict.

        Returns:
            PredictionResult with EMA prediction.
        """
        if not history:
            return PredictionResult(
                model=PredictionModel.EMA, fingerprint="",
                current_price=0, predicted_price=0,
                trend=TrendDirection.STABLE, confidence=0.1,
                history_points=0, horizon_days=horizon_days,
            )

        # Compute EMA from start
        ema = history[0].price
        for p in history[1:]:
            ema = self.alpha * p.price + (1 - self.alpha) * ema

        prices = [p.price for p in history]
        trend = _detect_trend(prices)
        conf = min(0.9, 0.3 + len(history) * 0.05)

        return PredictionResult(
            model=PredictionModel.EMA,
            fingerprint="",
            current_price=history[-1].price,
            predicted_price=round(ema, 2),
            trend=trend,
            confidence=conf,
            history_points=len(history),
            horizon_days=horizon_days,
        )


def _detect_trend(prices: list[float]) -> TrendDirection:
    """Detect price trend direction from recent observations.

    Args:
        prices: List of observed prices (chronological).

    Returns:
        TrendDirection enum value.
    """
    if len(prices) < 3:
        return TrendDirection.STABLE

    recent = prices[-5:] if len(prices) >= 5 else prices

    # Compute slope of recent prices
    n = len(recent)
    xs = list(range(n))
    denom = n * sum(x * x for x in xs) - sum(xs) ** 2
    if denom == 0:
        return TrendDirection.STABLE

    slope = (
        n * sum(x * y for x, y in zip(xs, recent))
        - sum(xs) * sum(recent)
    ) / denom

    # Detect volatility
    if len(recent) >= 3:
        diffs = [abs(recent[i] - recent[i - 1]) for i in range(1, len(recent))]
        avg_diff = sum(diffs) / len(diffs)
        avg_price = sum(recent) / len(recent)
        volatility = avg_diff / avg_price if avg_price > 0 else 0
        if volatility > 0.15:
            return TrendDirection.VOLATILE

    threshold = 0.01 * (sum(recent) / len(recent))
    if slope > threshold:
        return TrendDirection.UP
    elif slope < -threshold:
        return TrendDirection.DOWN
    else:
        return TrendDirection.STABLE


class PolynomialPredictor:
    """Polynomial regression price predictor.

    Fits y = c0 + c1*x + c2*x^2 + ... + c_degree*x^degree
    and extrapolates to predict future price.
    """

    def __init__(self, degree: int = 2, min_points: int = 5) -> None:
        """Initialize PolynomialPredictor.

        Args:
            degree: Polynomial degree (2=quadratic, 3=cubic).
            min_points: Minimum observations needed to fit.
        """
        self.degree = degree
        self.min_points = min_points

    def predict(
        self, history: list[PricePoint], horizon_days: int = 7, fingerprint: str = ""
    ) -> PredictionResult:
        """Predict future price using polynomial regression.

        Args:
            history: List of price observations sorted by day.
            horizon_days: Days ahead to predict.
            fingerprint: Product fingerprint for identification.

        Returns:
            PredictionResult with polynomial prediction.
        """
        if len(history) < self.min_points:
            model_type = (
                PredictionModel.LINEAR if self.degree == 1
                else PredictionModel.POLYNOMIAL_2 if self.degree == 2
                else PredictionModel.POLYNOMIAL_3
            )
            return PredictionResult(
                model=model_type,
                fingerprint=fingerprint,
                current_price=history[-1].price if history else 0,
                predicted_price=history[-1].price if history else 0,
                trend=TrendDirection.STABLE,
                confidence=0.1,
                history_points=len(history),
                horizon_days=horizon_days,
            )

        points = [(p.day, p.price) for p in history]
        coeffs = _fit_polynomial(points, self.degree)

        if not coeffs:
            return PredictionResult(
                model=PredictionModel.POLYNOMIAL_2 if self.degree == 2 else PredictionModel.POLYNOMIAL_3,
                fingerprint=fingerprint,
                current_price=history[-1].price,
                predicted_price=history[-1].price,
                trend=TrendDirection.STABLE,
                confidence=0.1,
                history_points=len(history),
                horizon_days=horizon_days,
            )

        # Extrapolate
        future_x = history[-1].day + horizon_days
        predicted = _eval_poly(coeffs, future_x)

        # Clamp: price should not go below 0
        predicted = max(0, predicted)

        # MSE for confidence
        mse = _mean_squared_error(points, coeffs)
        avg_price = sum(p.price for p in history) / len(history)
        # Confidence inversely proportional to relative MSE
        rel_mse = mse / (avg_price ** 2) if avg_price > 0 else 1.0
        confidence = max(0.1, min(0.95, 1.0 - rel_mse))

        prices = [p.price for p in history]
        trend = _detect_trend(prices)

        model_type = (
            PredictionModel.LINEAR if self.degree == 1
            else PredictionModel.POLYNOMIAL_2 if self.degree == 2
            else PredictionModel.POLYNOMIAL_3
        )

        return PredictionResult(
            model=model_type,
            fingerprint=fingerprint,
            current_price=history[-1].price,
            predicted_price=round(predicted, 2),
            trend=trend,
            confidence=round(confidence, 2),
            slope=coeffs[1] if len(coeffs) > 1 else 0.0,
            curvature=coeffs[2] if len(coeffs) > 2 else 0.0,
            residuals=round(mse, 2),
            history_points=len(history),
            horizon_days=horizon_days,
            metadata={"coefficients": coeffs, "mse": mse},
        )


class EnsemblePredictor:
    """Ensemble predictor combining linear, polynomial, and moving-average models.

    Averages predictions from multiple models weighted by their confidence.
    """

    def __init__(
        self,
        predictors: list | None = None,
        weights: list[float] | None = None,
    ) -> None:
        """Initialize EnsemblePredictor.

        Args:
            predictors: List of predictor instances. Default: all available.
            weights: Optional weights for each predictor (must match predictors count).
        """
        if predictors is None:
            self.predictors = [
                PolynomialPredictor(degree=1),     # Linear
                PolynomialPredictor(degree=2),     # Quadratic
                SimpleMovingAverage(window=5),
                ExponentialMovingAverage(window=5),
            ]
        else:
            self.predictors = predictors

        self.weights = weights or [1.0] * len(self.predictors)

    def predict(
        self, history: list[PricePoint], horizon_days: int = 7, fingerprint: str = ""
    ) -> PredictionResult:
        """Predict using ensemble of multiple models.

        Args:
            history: List of price observations sorted by day.
            horizon_days: Days ahead to predict.
            fingerprint: Product fingerprint.

        Returns:
            PredictionResult with ensemble-averaged prediction.
        """
        if not history:
            return PredictionResult(
                model=PredictionModel.ENSEMBLE,
                fingerprint=fingerprint,
                current_price=0,
                predicted_price=0,
                trend=TrendDirection.STABLE,
                confidence=0.0,
                history_points=0,
                horizon_days=horizon_days,
            )

        results: list[PredictionResult] = []
        for pred in self.predictors:
            if isinstance(pred, PolynomialPredictor):
                r = pred.predict(history, horizon_days, fingerprint)
            else:
                r = pred.predict(history, horizon_days)
                r.fingerprint = fingerprint
            results.append(r)

        # Weighted average by confidence × explicit weight
        total_weight = 0.0
        weighted_price = 0.0
        weighted_conf = 0.0

        for i, r in enumerate(results):
            w = r.confidence * self.weights[i]
            weighted_price += r.predicted_price * w
            weighted_conf += r.confidence * self.weights[i]
            total_weight += w

        if total_weight > 0:
            ensemble_price = weighted_price / total_weight
            ensemble_conf = weighted_conf / total_weight
        else:
            ensemble_price = history[-1].price
            ensemble_conf = 0.1

        prices = [p.price for p in history]
        trend = _detect_trend(prices)

        return PredictionResult(
            model=PredictionModel.ENSEMBLE,
            fingerprint=fingerprint,
            current_price=history[-1].price,
            predicted_price=round(ensemble_price, 2),
            trend=trend,
            confidence=round(ensemble_conf, 2),
            history_points=len(history),
            horizon_days=horizon_days,
            metadata={"individual_results": [r.__dict__ for r in results]},
        )


class PricePredictionEngine:
    """High-level price prediction engine combining all models.

    Provides:
    - predict(fingerprint, history, model_type) — single model
    - predict_best(fingerprint, history) — auto-select best model
    - predict_all(fingerprint, history) — all models + ensemble
    """

    def __init__(self) -> None:
        """Initialize PricePredictionEngine with all sub-models."""
        self.linear = PolynomialPredictor(degree=1, min_points=3)
        self.quadratic = PolynomialPredictor(degree=2, min_points=5)
        self.cubic = PolynomialPredictor(degree=3, min_points=7)
        self.sma = SimpleMovingAverage(window=5)
        self.wma = WeightedMovingAverage(window=5)
        self.ema = ExponentialMovingAverage(window=5)
        self.ensemble = EnsemblePredictor()

    def predict(
        self,
        fingerprint: str,
        history: list[PricePoint],
        model: PredictionModel = PredictionModel.ENSEMBLE,
        horizon_days: int = 7,
    ) -> PredictionResult:
        """Predict price using specified model.

        Args:
            fingerprint: Product fingerprint.
            history: Price observations.
            model: Which model to use.
            horizon_days: Days ahead to predict.

        Returns:
            PredictionResult from the specified model.
        """
        predictor_map = {
            PredictionModel.LINEAR: self.linear,
            PredictionModel.POLYNOMIAL_2: self.quadratic,
            PredictionModel.POLYNOMIAL_3: self.cubic,
            PredictionModel.SMA: self.sma,
            PredictionModel.WMA: self.wma,
            PredictionModel.EMA: self.ema,
            PredictionModel.ENSEMBLE: self.ensemble,
        }

        predictor = predictor_map.get(model, self.ensemble)
        if isinstance(predictor, PolynomialPredictor):
            return predictor.predict(history, horizon_days, fingerprint)
        elif isinstance(predictor, EnsemblePredictor):
            return predictor.predict(history, horizon_days, fingerprint)
        else:
            r = predictor.predict(history, horizon_days)
            r.fingerprint = fingerprint
            return r

    def predict_best(
        self,
        fingerprint: str,
        history: list[PricePoint],
        horizon_days: int = 7,
    ) -> PredictionResult:
        """Auto-select best model by confidence and predict.

        Runs all models and returns the one with highest confidence.

        Args:
            fingerprint: Product fingerprint.
            history: Price observations.
            horizon_days: Days ahead to predict.

        Returns:
            Best PredictionResult.
        """
        all_results = self.predict_all(fingerprint, history, horizon_days)
        best = max(all_results, key=lambda r: r.confidence)
        return best

    def predict_all(
        self,
        fingerprint: str,
        history: list[PricePoint],
        horizon_days: int = 7,
    ) -> list[PredictionResult]:
        """Run all prediction models and return all results.

        Args:
            fingerprint: Product fingerprint.
            history: Price observations.
            horizon_days: Days ahead to predict.

        Returns:
            List of PredictionResult from all models.
        """
        results = []
        for model_type in [
            PredictionModel.LINEAR,
            PredictionModel.POLYNOMIAL_2,
            PredictionModel.POLYNOMIAL_3,
            PredictionModel.SMA,
            PredictionModel.WMA,
            PredictionModel.EMA,
            PredictionModel.ENSEMBLE,
        ]:
            r = self.predict(fingerprint, history, model_type, horizon_days)
            results.append(r)
        return results
