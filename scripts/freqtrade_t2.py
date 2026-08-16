#!/usr/bin/env python3
"""T2 momentum strategy ported to Freqtrade.

The validated AIOS T2 strategy (7-year backtest, docs/T2_VALIDATION_AND_EXPANSION):
- enter LONG when close > SMA(in_w) and not in position
- exit when close <= SMA(out_w)  (hysteresis: in_w=50, out_w=40)
- BNB/NEAR use in_w=out_w=50 (no hysteresis)

For Freqtrade backtesting, hyperopt, and A/B comparison vs community
strategies (e.g. NostalgiaForInfinity).

Usage (in freqtrade dir):
    freqtrade backtesting --strategy T2Momentum --config config_t2.json
"""

from freqtrade.strategy import IStrategy, CategoricalParameter, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta


class T2Momentum(IStrategy):
    """T2: time-series momentum with SMA in/out hysteresis (daily bars)."""

    INTERFACE_VERSION = 3

    # ---- config (defaults from validation; hyperopt-able) ----
    in_w = IntParameter(30, 100, default=50, space="buy")
    out_w = IntParameter(20, 90, default=40, space="sell")

    # ---- risk ----
    stoploss = -0.99  # no hard stoploss: SMA exit is the protection
    trailing_stop = False
    use_custom_stoploss = False

    # ---- execution ----
    timeframe = "1d"
    can_short = False
    startup_candle_count = 200
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # ---- ROI ----
    minimal_roi = {"0": 100}  # disable ROI exits; only SMA exit

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma_in"] = ta.SMA(dataframe, timeperiod=self.in_w.value)
        dataframe["sma_out"] = ta.SMA(dataframe, timeperiod=self.out_w.value)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["sma_in"])
            & (dataframe["close"].shift(1) <= dataframe["sma_in"].shift(1)),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["sma_out"])
            & (dataframe["close"].shift(1) >= dataframe["sma_out"].shift(1)),
            "exit_long",
        ] = 1
        return dataframe
