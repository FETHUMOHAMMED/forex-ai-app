"""Deterministic, offline fixtures for the verified legacy V3 path.

The fixtures deliberately load the legacy modules behind a fake MT5 module and
disable their file logging.  They are characterization support, not adapters
used by production code.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
from types import ModuleType, SimpleNamespace

import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AI_SERVICE = os.path.join(ROOT, "ai-service")


class FakeMT5(ModuleType):
    """Small MT5 stand-in that records requests and never contacts a terminal."""

    TIMEFRAME_M15 = 15
    TIMEFRAME_H1 = 60
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_SLTP = 6
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    ORDER_TIME_GTC = 0
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_REQUOTE = 10004
    TRADE_RETCODE_OFF_QUOTES = 10006
    TRADE_RETCODE_TRADE_CONTEXT_BUSY = 10013
    TRADE_RETCODE_NO_MONEY = 10019
    TRADE_RETCODE_MARKET_CLOSED = 10018
    TRADE_RETCODE_INVALID_STOPS = 10016

    def __init__(self):
        super().__init__("MetaTrader5")
        self.requests = []
        self.order_results = []
        self.selected = []
        self.initialized = True
        self.logged_in = REDACTED_LIVE_ACCOUNT
        self.tick = SimpleNamespace(ask=1.10007, bid=1.09997, time=2_000_000_000)
        self.info = SimpleNamespace(
            point=0.00001,
            digits=5,
            filling_mode=1,
            trade_mode=1,
            trade_tick_value=1.0,
            trade_tick_size=0.00001,
        )
        self.account = SimpleNamespace(login=self.logged_in, margin_free=10_000.0)
        self.positions = []

    def initialize(self):
        self.initialized = True
        return True

    def shutdown(self):
        return True

    def terminal_info(self):
        return SimpleNamespace()

    def login(self, account, password=None, server=None):
        self.logged_in = account
        self.account.login = account
        return True

    def account_info(self):
        self.account.login = self.logged_in
        return self.account

    def symbol_select(self, symbol, enabled):
        if enabled:
            self.selected.append(symbol)
        return True

    def symbol_info(self, symbol):
        return self.info

    def symbol_info_tick(self, symbol):
        return self.tick

    def order_calc_margin(self, trade_type, symbol, volume, price):
        return 100.0

    def positions_get(self, symbol=None):
        if symbol is None:
            return list(self.positions)
        return [p for p in self.positions if p.symbol == symbol]

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        return []

    def history_deals_get(self, *args, **kwargs):
        return []

    def order_send(self, request):
        self.requests.append(dict(request))
        if self.order_results:
            return self.order_results.pop(0)
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, comment="done", order=123456)

    def last_error(self):
        return (0, "ok")


def load_legacy_modules():
    """Load legacy modules without MT5 access or repository log writes."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    if AI_SERVICE not in sys.path:
        sys.path.insert(0, AI_SERVICE)
    mt5 = FakeMT5()
    sys.modules["MetaTrader5"] = mt5

    original_basic_config = logging.basicConfig
    original_file_handler = logging.FileHandler
    logging.basicConfig = lambda *args, **kwargs: None
    try:
        for name in ("real_ai_service", "ai_service_daemon", "broker_exness", "auto_trader_exness"):
            sys.modules.pop(name, None)
        # Load third-party logging users before replacing FileHandler.  The
        # daemon's module-level logging setup is then isolated without
        # breaking logging.handlers.BaseRotatingHandler inheritance.
        importlib.import_module("uvicorn")
        importlib.import_module("fastapi")
        logging.FileHandler = lambda *args, **kwargs: logging.NullHandler()
        signal = importlib.import_module("real_ai_service")
        daemon = importlib.import_module("ai_service_daemon")
        broker = importlib.import_module("broker_exness")
        execution = importlib.import_module("auto_trader_exness")
    finally:
        logging.basicConfig = original_basic_config
        logging.FileHandler = original_file_handler
    return signal, daemon, broker, execution, mt5


class FakeModel:
    def __init__(self, direction="BUY", confidence=0.80, fail=False):
        self.direction = direction
        self.confidence = confidence
        self.fail = fail

    def predict_proba(self, frame):
        if self.fail:
            raise RuntimeError("model failure")
        if self.direction == "BUY":
            return [[1.0 - self.confidence, self.confidence]]
        return [[self.confidence, 1.0 - self.confidence]]

    def predict(self, frame):
        if self.fail:
            raise RuntimeError("model failure")
        return [1 if self.direction == "BUY" else 0]


class FakeMicrostructure:
    def __init__(self, score=81.85):
        self.score = score

    def analyze(self, pair, frame):
        return SimpleNamespace(
            institutional_bias="BREAKOUT",
            microstructure_score=self.score,
            dealer_pressure="SELLING_PRESSURE",
            liquidity_state="SWEEP_SELL",
            continuation_probability=0.50,
            manipulation_probability=0.10,
            expansion_quality=0.80,
            price_discovery="DISCOVERY",
        )


class FakeLiquidity:
    def analyze(self, pair, frame):
        return SimpleNamespace(
            nearest_liquidity="NONE", sweep_strength=0.5,
            sweep_direction=None, liquidity_score=70
        )


class FakeStructure:
    def analyze(self, pair, frame):
        return SimpleNamespace(
            market_phase="TRENDING", structure_bias="TRENDING_BEAR",
            structure_score=75, continuation_probability=0.5
        )


def signal_frame(direction="BUY", confidence=0.80, institutional_score=81.85,
                 atr=0.001, h4="aligned"):
    """Return 120 deterministic M15 rows suitable for get_real_signal."""
    index = pd.date_range("2026-01-05", periods=120, freq="15min", tz="UTC")
    frame = pd.DataFrame({
        "open": 1.0995, "high": 1.1010, "low": 1.0990,
        "close": 1.1000, "volume": 1000.0,
    }, index=index)
    frame["atr"] = atr
    for name in ("rsi", "macd", "macd_signal", "volume_ratio", "dist_from_h4_ema",
                 "london", "newyork", "vol_high", "returns", "high_low_ratio"):
        frame[name] = 0.0
    for name in ("fvg_buy", "fvg_sell", "ob_buy", "ob_sell", "mss_buy", "mss_sell",
                 "bb_buy", "bb_sell", "lv_buy", "lv_sell"):
        frame[name] = 0

    previous = frame.index[-2]
    if direction == "BUY":
        frame.loc[previous, ["mss_buy", "ob_buy"]] = 1
        frame.loc[previous, ["fvg_sell", "ob_sell", "mss_sell", "bb_sell", "lv_sell"]] = 0
        frame.loc[frame.index[-1], "h4_uptrend"] = 1 if h4 == "aligned" else 0
        frame.loc[frame.index[-1], "h4_downtrend"] = 0
    else:
        frame.loc[previous, ["mss_sell", "ob_sell"]] = 1
        frame.loc[previous, ["fvg_buy", "ob_buy", "mss_buy", "bb_buy", "lv_buy"]] = 0
        frame.loc[frame.index[-1], "h4_downtrend"] = 1 if h4 == "aligned" else 0
        frame.loc[frame.index[-1], "h4_uptrend"] = 0
    frame.attrs["institutional_score"] = institutional_score
    return frame


def configured_signal_trader(signal_module, direction="BUY", confidence=0.80,
                             institutional_score=81.85, atr=0.001, trend=None,
                             h4="aligned", model_failure=False):
    trader = signal_module.RealAITrader.__new__(signal_module.RealAITrader)
    frame = signal_frame(direction, confidence, institutional_score, atr, h4)
    trader.models = {"EURUSD": FakeModel(direction, confidence, model_failure)}
    trader.fetch_data = lambda pair: frame.copy()
    trader.add_indicators = lambda value: value.copy()
    trader.get_higher_tf_trend = lambda pair: trend or ("BULLISH" if direction == "BUY" else "BEARISH")
    trader.microstructure = FakeMicrostructure(institutional_score)
    trader.liquidity_engine = FakeLiquidity()
    trader.structure_engine = FakeStructure()
    trader.performance_engine = SimpleNamespace()
    trader.rejected_trend = 0
    trader.rejected_no_ict = 0
    trader.rejected_low_conf = 0
    trader.accepted = 0
    return trader


def cache_signal(pair="EURUSD", direction="BUY", confidence=0.83):
    return {
        "pair": pair, "signal": direction, "confidence": confidence,
        "strength": "STRONG", "entry": 1.15123, "stop_loss": 1.15299,
        "take_profit": 1.14842, "atr": 0.001, "risk_reward": 1.6,
        "timestamp": "2026-08-13T07:54:38+00:00", "regime": "volatile",
        "institutional_bias": "BREAKOUT", "institutional_score": 81.85,
        "dealer_pressure": "SELLING_PRESSURE", "liquidity_state": "SWEEP_SELL",
        "continuation_prob": 0.5,
    }
