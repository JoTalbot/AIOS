#!/usr/bin/env python3
"""
AIOS Quant ML Engine - Инференс обученных моделей на VPS (Этап 2.3)

Загружает модели, обученные в Colab (data/quant/models/), собирает свежие
признаки из data/quant/<SYMBOL>/<EXCHANGE>/*.csv и выдаёт прогноз направления
цены. Является одним из источников сигналов для quant_trading_engine.py.

Ожидаемые файлы моделей в data/quant/models/:
  - catboost_price_dir.cbm / .pkl   (классификатор направления, CatBoost)
  - ppo_trader.zip                   (RL-агент, Stable-Baselines3)

Если модели нет -> модуль сообщает, что нужно обучение в Colab
(docs/AIOS_Colab_Quant_ML_Training.ipynb).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
QUANT_DIR = REPO_ROOT / "data" / "quant"
MODELS_DIR = QUANT_DIR / "models"

LOG_TAG = "[QuantMLPredictor]"

DEFAULT_FEATURES = ["open", "high", "low", "close", "volume", "ret1", "ema12", "ema26", "rsi", "vol_ma"]


class QuantMLPredictor:
    """Предсказание направления цены на основе обученной модели."""

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = Path(models_dir or MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._load_model()

    # ------------------------------------------------------------ loading ----
    def _load_model(self) -> None:
        """Загрузить CatBoost-модель если она есть."""
        candidates = [
            self.models_dir / "catboost_price_dir.cbm",
            self.models_dir / "catboost_price_dir.pkl",
        ]
        for p in candidates:
            if not p.exists():
                continue
            try:
                if p.suffix == ".cbm":
                    from catboost import CatBoostClassifier
                    self._model = CatBoostClassifier()
                    self._model.load_model(str(p))
                else:
                    import joblib
                    self._model = joblib.load(str(p))
                print(f"{LOG_TAG} Модель загружена: {p}")
                return
            except Exception as e:
                print(f"{LOG_TAG} [WARN] Не удалось загрузить {p}: {e}")

    @property
    def available(self) -> bool:
        return self._model is not None

    # -------------------------------------------------------- prediction ----
    def _features_from_csv(self, csv_path: Path) -> Optional[list]:
        """Построить вектор признаков из последних строк CSV."""
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"{LOG_TAG} [WARN] CSV {csv_path}: {e}")
            return None
        if len(df) < 26:
            return None
        df = df.sort_values("timestamp_ms")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        g = df[["open", "high", "low", "close", "volume"]].copy()
        g["ret1"] = g["close"].pct_change()
        g["ema12"] = g["close"].ewm(span=12).mean()
        g["ema26"] = g["close"].ewm(span=26).mean()
        g["rsi"] = 100 - 100 / (1 + g["close"].pct_change().rolling(14).mean() /
                                g["close"].pct_change().rolling(14).std().replace(0, 1e-9))
        g["vol_ma"] = g["volume"].rolling(20).mean()
        last = g.dropna().iloc[-1]
        try:
            return [float(last[c]) for c in DEFAULT_FEATURES]
        except Exception:
            return None

    def predict_symbol(self, symbol: str, exchange: str = "binance", timeframe: str = "1h") -> Optional[dict]:
        """Прогноз для одного актива на основе последнего CSV."""
        if not self.available:
            return {"symbol": symbol, "ok": False,
                    "error": "Модель не обучена. Запустите Colab-ноутбук Quant ML Training."}
        csv_candidates = [
            self._find_csv(symbol, exchange, timeframe),
            self._find_any_csv(symbol, timeframe),
        ]
        feat = None
        used = None
        for csv_path in csv_candidates:
            if csv_path and csv_path.exists():
                feat = self._features_from_csv(csv_path)
                if feat:
                    used = csv_path
                    break
        if feat is None:
            return {"symbol": symbol, "ok": False,
                    "error": f"Недостаточно данных в data/quant/{symbol}"}

        proba = self._model.predict_proba([feat])[0]
        pred = self._model.predict([feat])[0]
        return {
            "symbol": symbol,
            "ok": True,
            "direction": "UP" if int(pred) == 1 else "DOWN",
            "prob_up": round(float(proba[1]), 4),
            "prob_down": round(float(proba[0]), 4),
            "source": str(used),
            "model": str(self.models_dir),
        }

    def predict_all(self, symbols: Optional[list[str]] = None) -> list[dict]:
        """Прогноз по всем активам, для которых есть данные."""
        if not self.available:
            return [{"ok": False, "error": "Модель не обучена. Запустите Colab-ноутбук Quant ML Training."}]
        if symbols is None:
            symbols = sorted(d.name for d in QUANT_DIR.iterdir()
                             if d.is_dir() and not d.name.startswith("_") and d.name not in ("export", "models", "uniswap_v3"))
        out = []
        for s in symbols:
            r = self.predict_symbol(s)
            if r.get("ok"):
                out.append(r)
        return out

    # ------------------------------------------------------------- utils ----
    def _find_csv(self, symbol: str, exchange: str, timeframe: str) -> Optional[Path]:
        return self.models_dir.parent / symbol / exchange / f"{symbol}_{timeframe}.csv"

    def _find_any_csv(self, symbol: str, timeframe: str) -> Optional[Path]:
        d = self.models_dir.parent / symbol
        if not d.exists():
            return None
        for f in d.rglob(f"*_{timeframe}.csv"):
            return f
        return None

    def signal_json(self) -> dict:
        """Полный отчёт по сигналам для quant_trading_engine.py."""
        from datetime import datetime, timezone
        return {
            "engine": "quant_ml_predictor",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_available": self.available,
            "signals": self.predict_all(),
        }


if __name__ == "__main__":
    import sys
    predictor = QuantMLPredictor()
    print(json.dumps(predictor.signal_json(), indent=2, ensure_ascii=False))
