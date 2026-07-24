"""Tests for price_prediction_ml module — polynomial regression and moving-average forecasting."""

from __future__ import annotations

from aios_core.price_prediction_ml import (
    EnsemblePredictor,
    ExponentialMovingAverage,
    PolynomialPredictor,
    PredictionModel,
    PricePoint,
    PricePredictionEngine,
    SimpleMovingAverage,
    TrendDirection,
    WeightedMovingAverage,
    _detect_trend,
    _eval_poly,
    _fit_polynomial,
    _gauss_solve,
    _mean_squared_error,
)

# ─── Helper ───

def _make_history(prices: list[float]) -> list[PricePoint]:
    """Create PricePoint history from price list."""
    return [PricePoint(day=i, price=p) for i, p in enumerate(prices)]


# ─── Polynomial fitting ───

class TestPolynomialFit:
    """Tests for _fit_polynomial and _gauss_solve."""

    def test_linear_fit_two_points(self) -> None:
        """Two points → exact linear fit."""
        points = [(0, 10), (10, 20)]
        coeffs = _fit_polynomial(points, 1)
        assert len(coeffs) == 2
        # y = 10 + 1*x
        assert abs(coeffs[0] - 10) < 0.01
        assert abs(coeffs[1] - 1) < 0.01

    def test_linear_fit_three_points(self) -> None:
        """Three collinear points → exact linear fit."""
        points = [(0, 100), (5, 110), (10, 120)]
        coeffs = _fit_polynomial(points, 1)
        assert len(coeffs) == 2
        assert abs(coeffs[0] - 100) < 0.1
        assert abs(coeffs[1] - 2) < 0.01

    def test_quadratic_fit(self) -> None:
        """Quadratic points → exact quadratic fit."""
        # y = 1 + 2*x + 3*x^2
        points = [(0, 1), (1, 6), (2, 17), (3, 34), (4, 57)]
        coeffs = _fit_polynomial(points, 2)
        assert len(coeffs) == 3
        assert abs(coeffs[0] - 1) < 0.5
        assert abs(coeffs[1] - 2) < 0.5
        assert abs(coeffs[2] - 3) < 0.5

    def test_insufficient_points_returns_empty(self) -> None:
        """Too few points → empty coefficients."""
        points = [(0, 10), (5, 20)]
        coeffs = _fit_polynomial(points, 3)
        assert coeffs == []

    def test_gauss_solve_identity(self) -> None:
        """Identity matrix → solution equals b."""
        A = [[1, 0], [0, 1]]
        b = [3, 7]
        x = _gauss_solve(A, b, 2)
        assert abs(x[0] - 3) < 1e-10
        assert abs(x[1] - 7) < 1e-10

    def test_gauss_solve_2x2(self) -> None:
        """Simple 2×2 system."""
        A = [[2, 1], [5, 7]]
        b = [11, 13]
        x = _gauss_solve(A, b, 2)
        # 2x + y = 11, 5x + 7y = 13 → x=7.69, y=-4.38
        assert abs(2 * x[0] + x[1] - 11) < 1e-6
        assert abs(5 * x[0] + 7 * x[1] - 13) < 1e-6

    def test_eval_poly(self) -> None:
        """Evaluate polynomial at x."""
        coeffs = [1, 2, 3]  # y = 1 + 2x + 3x^2
        assert abs(_eval_poly(coeffs, 0) - 1) < 1e-10
        assert abs(_eval_poly(coeffs, 1) - 6) < 1e-10
        assert abs(_eval_poly(coeffs, 2) - 17) < 1e-10

    def test_mse(self) -> None:
        """MSE of perfect fit should be ~0."""
        # Points from y = 10 + 2x
        points = [(0, 10), (1, 12), (2, 14)]
        coeffs = [10, 2]
        mse = _mean_squared_error(points, coeffs)
        assert mse < 0.01


# ─── Trend detection ───

class TestTrendDetection:
    """Tests for _detect_trend."""

    def test_stable_flat_prices(self) -> None:
        """Flat prices → stable."""
        trend = _detect_trend([100, 100, 100, 100, 100])
        assert trend == TrendDirection.STABLE

    def test_up_trend(self) -> None:
        """Rising prices → up."""
        trend = _detect_trend([100, 105, 110, 115, 120])
        assert trend == TrendDirection.UP

    def test_down_trend(self) -> None:
        """Falling prices → down."""
        trend = _detect_trend([120, 115, 110, 105, 100])
        assert trend == TrendDirection.DOWN

    def test_volatile_prices(self) -> None:
        """Wildly fluctuating prices → volatile."""
        trend = _detect_trend([100, 200, 50, 300, 10])
        assert trend == TrendDirection.VOLATILE

    def test_short_history_stable(self) -> None:
        """Less than 3 points → stable default."""
        trend = _detect_trend([100])
        assert trend == TrendDirection.STABLE


# ─── SMA ───

class TestSimpleMovingAverage:
    """Tests for SimpleMovingAverage."""

    def test_basic_prediction(self) -> None:
        """SMA predicts average of last window."""
        sma = SimpleMovingAverage(window=3)
        history = _make_history([100, 110, 120, 130, 140])
        result = sma.predict(history)
        # Last 3: 120, 130, 140 → avg = 130
        assert abs(result.predicted_price - 130) < 1

    def test_insufficient_data(self) -> None:
        """Fewer points than window → average of all."""
        sma = SimpleMovingAverage(window=5)
        history = _make_history([100, 110])
        result = sma.predict(history)
        assert abs(result.predicted_price - 105) < 1

    def test_empty_history(self) -> None:
        """Empty history → 0 price."""
        sma = SimpleMovingAverage(window=5)
        result = sma.predict([])
        assert result.predicted_price == 0

    def test_confidence_increases_with_data(self) -> None:
        """More data → higher confidence."""
        sma = SimpleMovingAverage(window=3)
        r1 = sma.predict(_make_history([100, 110, 120]))
        r2 = sma.predict(_make_history(range(100, 200)))
        assert r2.confidence > r1.confidence


# ─── WMA ───

class TestWeightedMovingAverage:
    """Tests for WeightedMovingAverage."""

    def test_weighted_prediction(self) -> None:
        """WMA gives more weight to recent prices."""
        wma = WeightedMovingAverage(window=3)
        history = _make_history([100, 110, 120])
        result = wma.predict(history)
        # Weights: 1, 2, 3 → weighted avg = (100*1 + 110*2 + 120*3) / 6 = 113.33
        assert abs(result.predicted_price - 113.33) < 1

    def test_insufficient_data(self) -> None:
        """Fewer points than window → simple average."""
        wma = WeightedMovingAverage(window=5)
        history = _make_history([100, 110])
        result = wma.predict(history)
        assert abs(result.predicted_price - 105) < 1


# ─── EMA ───

class TestExponentialMovingAverage:
    """Tests for ExponentialMovingAverage."""

    def test_ema_prediction(self) -> None:
        """EMA converges towards recent prices."""
        ema = ExponentialMovingAverage(window=3)
        history = _make_history([100, 110, 120, 130])
        result = ema.predict(history)
        # EMA should be between 100 and 130
        assert 100 < result.predicted_price < 130

    def test_ema_single_point(self) -> None:
        """Single point → EMA equals that point."""
        ema = ExponentialMovingAverage(window=5)
        history = _make_history([150])
        result = ema.predict(history)
        assert abs(result.predicted_price - 150) < 1

    def test_ema_empty_history(self) -> None:
        """Empty history → 0."""
        ema = ExponentialMovingAverage(window=5)
        result = ema.predict([])
        assert result.predicted_price == 0

    def test_ema_smoothing(self) -> None:
        """EMA smooths noisy data."""
        ema = ExponentialMovingAverage(window=5)
        noisy = _make_history([100, 200, 100, 200, 100])
        smooth_result = ema.predict(noisy)
        # EMA should be much less volatile than raw prices
        assert abs(smooth_result.predicted_price - 100) < 80


# ─── Polynomial predictor ───

class TestPolynomialPredictor:
    """Tests for PolynomialPredictor."""

    def test_linear_prediction(self) -> None:
        """Linear predictor extrapolates linearly."""
        pred = PolynomialPredictor(degree=1, min_points=3)
        history = _make_history([100, 110, 120, 130, 140])
        result = pred.predict(history, horizon_days=7, fingerprint="fp_1")
        # Linear: price increases 10/day → 140 + 7*10 = 210
        assert result.predicted_price > 150
        assert result.fingerprint == "fp_1"

    def test_quadratic_prediction(self) -> None:
        """Quadratic predictor captures curvature."""
        pred = PolynomialPredictor(degree=2, min_points=5)
        # Curving prices: 100, 105, 115, 130, 150
        history = _make_history([100, 105, 115, 130, 150])
        result = pred.predict(history, horizon_days=7)
        # Should predict higher than linear due to acceleration
        assert result.curvature != 0.0 or result.slope > 0

    def test_insufficient_data(self) -> None:
        """Too few points → fallback to current price."""
        pred = PolynomialPredictor(degree=2, min_points=5)
        history = _make_history([100, 110])
        result = pred.predict(history, fingerprint="fp_short")
        assert abs(result.predicted_price - 110) < 1
        assert result.confidence <= 0.2

    def test_no_negative_prediction(self) -> None:
        """Predicted price should not go below 0."""
        pred = PolynomialPredictor(degree=1, min_points=3)
        # Declining prices that might extrapolate to negative
        history = _make_history([100, 50, 10])
        result = pred.predict(history, horizon_days=100)
        assert result.predicted_price >= 0


# ─── Ensemble predictor ───

class TestEnsemblePredictor:
    """Tests for EnsemblePredictor."""

    def test_ensemble_prediction(self) -> None:
        """Ensemble averages multiple models."""
        ensemble = EnsemblePredictor()
        history = _make_history([100, 105, 110, 115, 120, 125, 130])
        result = ensemble.predict(history, horizon_days=7, fingerprint="fp_ens")
        # Should be somewhere between SMA and polynomial predictions
        assert 130 < result.predicted_price < 250
        assert result.fingerprint == "fp_ens"

    def test_ensemble_empty_history(self) -> None:
        """Empty history → 0."""
        ensemble = EnsemblePredictor()
        result = ensemble.predict([], fingerprint="fp_empty")
        assert result.predicted_price == 0

    def test_custom_weights(self) -> None:
        """Custom weights bias ensemble towards specified models."""
        # Weight everything towards SMA
        ensemble = EnsemblePredictor(
            predictors=[SimpleMovingAverage(window=3), PolynomialPredictor(degree=1)],
            weights=[10.0, 0.1],
        )
        history = _make_history([100, 110, 120])
        result = ensemble.predict(history, fingerprint="fp_weighted")
        # Should be close to SMA (avg = 110)
        assert abs(result.predicted_price - 110) < 20


# ─── PricePredictionEngine ───

class TestPricePredictionEngine:
    """Tests for the high-level PricePredictionEngine."""

    def test_predict_specific_model(self) -> None:
        """Predict with a specific model type."""
        engine = PricePredictionEngine()
        history = _make_history([100, 105, 110, 115, 120, 125, 130])
        result = engine.predict("fp1", history, PredictionModel.SMA, horizon_days=7)
        assert result.model == PredictionModel.SMA

    def test_predict_linear(self) -> None:
        """Linear model prediction."""
        engine = PricePredictionEngine()
        history = _make_history([100, 110, 120, 130])
        result = engine.predict("fp_lin", history, PredictionModel.LINEAR)
        assert result.model == PredictionModel.LINEAR

    def test_predict_ensemble_default(self) -> None:
        """Default model is ensemble."""
        engine = PricePredictionEngine()
        history = _make_history(range(100, 110))
        result = engine.predict("fp_def", history)
        assert result.model == PredictionModel.ENSEMBLE

    def test_predict_best(self) -> None:
        """predict_best selects highest-confidence model."""
        engine = PricePredictionEngine()
        history = _make_history([100, 105, 110, 115, 120, 125, 130, 135, 140, 145])
        best = engine.predict_best("fp_best", history)
        # Best should have reasonable confidence
        assert best.confidence > 0.0
        assert best.predicted_price > 0

    def test_predict_all(self) -> None:
        """predict_all returns results from all models."""
        engine = PricePredictionEngine()
        history = _make_history([100, 105, 110, 115, 120, 125, 130])
        all_results = engine.predict_all("fp_all", history)
        assert len(all_results) == 7  # 7 model types
        models = [r.model for r in all_results]
        assert PredictionModel.ENSEMBLE in models
        assert PredictionModel.LINEAR in models
        assert PredictionModel.SMA in models

    def test_predict_all_empty_history(self) -> None:
        """Empty history → low confidence across all models."""
        engine = PricePredictionEngine()
        all_results = engine.predict_all("fp_empty", [])
        assert len(all_results) == 7
        for r in all_results:
            assert r.confidence <= 0.2

    def test_up_trend_detected(self) -> None:
        """Price prediction detects upward trend."""
        engine = PricePredictionEngine()
        history = _make_history([100, 110, 120, 130, 140, 150])
        result = engine.predict("fp_up", history, PredictionModel.LINEAR)
        assert result.trend == TrendDirection.UP

    def test_down_trend_detected(self) -> None:
        """Price prediction detects downward trend."""
        engine = PricePredictionEngine()
        history = _make_history([150, 140, 130, 120, 110, 100])
        result = engine.predict("fp_down", history, PredictionModel.LINEAR)
        assert result.trend == TrendDirection.DOWN

    def test_stable_trend_detected(self) -> None:
        """Flat prices → stable trend."""
        engine = PricePredictionEngine()
        history = _make_history([100, 100, 100, 100, 100])
        result = engine.predict("fp_stable", history, PredictionModel.SMA)
        assert result.trend == TrendDirection.STABLE
