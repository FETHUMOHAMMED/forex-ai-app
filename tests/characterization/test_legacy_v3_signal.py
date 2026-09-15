"""Characterization tests for ai_service_daemon -> RealAITrader."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, mock_open, patch

from legacy_v3_fixtures import (
    cache_signal,
    configured_signal_trader,
    load_legacy_modules,
    signal_frame,
    ROOT,
)


class LegacyV3SignalCharacterization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signal, cls.daemon, _broker, _execution, cls.mt5 = load_legacy_modules()

    def test_normal_buy_captures_live_payload(self):
        trader = configured_signal_trader(self.signal, "BUY", 0.80)
        result = trader.get_real_signal("EURUSD")

        self.assertEqual(result["pair"], "EURUSD")
        self.assertEqual(result["signal"], "BUY")
        self.assertEqual(result["confidence"], 0.80)
        self.assertEqual(result["entry"], 1.1)
        self.assertEqual(result["stop_loss"], 1.0975)
        self.assertEqual(result["take_profit"], 1.104)
        self.assertEqual(result["risk_reward"], 1.6)
        self.assertEqual(result["regime"], "volatile")
        self.assertEqual(result["institutional_bias"], "BREAKOUT")
        self.assertEqual(result["institutional_score"], 81.85)
        self.assertEqual(result["dealer_pressure"], "SELLING_PRESSURE")
        self.assertEqual(result["liquidity_state"], "SWEEP_SELL")
        self.assertEqual(result["continuation_prob"], 0.5)
        self.assertIsNotNone(result["timestamp"])

    def test_normal_sell_captures_live_payload(self):
        trader = configured_signal_trader(self.signal, "SELL", 0.80)
        result = trader.get_real_signal("EURUSD")

        self.assertEqual(result["signal"], "SELL")
        self.assertEqual(result["confidence"], 0.80)
        self.assertEqual(result["entry"], 1.1)
        self.assertEqual(result["stop_loss"], 1.1025)
        self.assertEqual(result["take_profit"], 1.096)

    def test_fixture_captures_m15_features_and_legacy_metadata_absence(self):
        frame = signal_frame("BUY")
        self.assertEqual(len(frame), 120)
        self.assertEqual((frame.index[-1] - frame.index[-2]).total_seconds(), 900)
        self.assertEqual(frame.iloc[-1]["close"], 1.1)
        self.assertEqual(frame.iloc[-1]["atr"], 0.001)
        self.assertEqual(frame.iloc[-2]["mss_buy"], 1)
        self.assertEqual(frame.iloc[-2]["ob_buy"], 1)

        trader = configured_signal_trader(self.signal, "BUY", 0.80)
        result = trader.get_real_signal("EURUSD")
        for absent in ("session", "expires_at", "model_version", "strategy_version", "filter_version"):
            self.assertNotIn(absent, result)
        self.assertNotIn("rejection_reason", result)

    def test_backtest_helper_buy_and_sell_are_separate_legacy_behavior(self):
        trader = self.signal.RealAITrader.__new__(self.signal.RealAITrader)
        trader.models = {"EURUSD": _Model("BUY", 0.80)}
        buy = trader.get_signal_from_row(signal_frame("BUY").iloc[-2], "EURUSD")
        self.assertEqual(buy, {
            "pair": "EURUSD", "signal": "BUY", "confidence": 0.80,
            "entry": 1.1, "stop_loss": 1.0985, "take_profit": 1.1025,
        })

        trader.models = {"EURUSD": _Model("SELL", 0.80)}
        sell = trader.get_signal_from_row(signal_frame("SELL").iloc[-2], "EURUSD")
        self.assertEqual(sell["pair"], "EURUSD")
        self.assertEqual(sell["signal"], "SELL")
        self.assertEqual(sell["confidence"], 0.80)
        self.assertAlmostEqual(sell["entry"], 1.1)
        self.assertAlmostEqual(sell["stop_loss"], 1.1015)
        self.assertAlmostEqual(sell["take_profit"], 1.0975)

    def test_no_trade_when_ml_and_ict_disagree(self):
        trader = self.signal.RealAITrader.__new__(self.signal.RealAITrader)
        trader.models = {"EURUSD": _Model("SELL", 0.80)}
        row = signal_frame("BUY").iloc[-2]
        self.assertIsNone(trader.get_signal_from_row(row, "EURUSD"))

    def test_low_confidence_rejection_is_preserved(self):
        # H4 contradiction and counter-trend adjustment reduce 0.55 below 0.50.
        trader = configured_signal_trader(
            self.signal, "SELL", 0.55, trend="BULLISH", h4="contradictory"
        )
        self.assertIsNone(trader.get_real_signal("EURUSD"))

    def test_atr_filter_rejection_is_preserved(self):
        trader = self.signal.RealAITrader.__new__(self.signal.RealAITrader)
        trader.models = {"EURUSD": _Model("BUY", 0.80)}
        self.assertIsNone(
            trader.get_signal_from_row(signal_frame("BUY", atr=0.0001).iloc[-2], "EURUSD")
        )

    def test_institutional_score_rejection_is_preserved(self):
        trader = configured_signal_trader(self.signal, "BUY", 0.80, institutional_score=54)
        self.assertIsNone(trader.get_real_signal("EURUSD"))

    def test_missing_data_is_no_signal(self):
        trader = self.signal.RealAITrader.__new__(self.signal.RealAITrader)
        trader.fetch_data = lambda pair: None
        self.assertIsNone(trader.get_real_signal("EURUSD"))

    def test_model_failure_is_no_signal(self):
        trader = configured_signal_trader(self.signal, "BUY", 0.80, model_failure=True)
        self.assertIsNone(trader.get_real_signal("EURUSD"))

    def test_mock_fallback_is_opt_in_and_unmodified(self):
        trader = self.signal.RealAITrader.__new__(self.signal.RealAITrader)
        trader.use_mock_fallback = False
        trader.get_real_signal = lambda pair: None
        self.assertIsNone(trader.get_signal("EURUSD"))

        trader.use_mock_fallback = True
        trader.fetch_data = lambda pair: None
        result = trader.get_signal("EURUSD")
        self.assertEqual(result["pair"], "EURUSD")
        self.assertIn(result["signal"], ("BUY", "SELL"))
        self.assertGreaterEqual(result["confidence"], 0.65)
        self.assertLessEqual(result["confidence"], 0.85)
        self.assertEqual(result["entry"], 1.0925)
        self.assertIn(result["strength"], ("STRONG", "MEDIUM", "WEAK"))
        self.assertEqual(result["risk_reward"], 1.67)

    def test_signal_service_cache_schema_and_pair_endpoint(self):
        class ServiceDouble:
            pairs = ["EURUSD"]

            def get_signal(self, pair):
                return cache_signal(pair=pair)

        saved = json.loads((Path(ROOT) / "ai-service" / "signals_cache.json").read_text())
        self.assertEqual(
            set(saved), {"signals", "version", "last_update", "saved_at"}
        )
        self.assertIn("pair", saved["signals"][0])

        service = self.daemon.SignalService.__new__(self.daemon.SignalService)
        service.signals = [cache_signal()]
        service.signal_version = 51
        service.last_update = "2026-08-19T17:16:03+00:00"
        service.lock = threading.Lock()
        service.analyze_pair = lambda pair: cache_signal(pair=pair)
        self.daemon.signal_service = service
        response = asyncio.run(self.daemon.get_pair_signal("EURUSD"))
        self.assertEqual(set(response), {"signal", "cached"})
        self.assertTrue(response["cached"])
        self.assertEqual(response["signal"]["signal"], "BUY")

        fresh = asyncio.run(self.daemon.get_pair_signal("GBPUSD"))
        self.assertFalse(fresh["cached"])
        self.assertEqual(fresh["signal"]["pair"], "GBPUSD")

    def test_cache_deserialization_restores_legacy_fields(self):
        service = self.daemon.SignalService.__new__(self.daemon.SignalService)
        service.signals = []
        service.signal_version = 0
        service.last_update = None
        fake_path = Mock()
        fake_path.exists.return_value = True
        payload = {
            "signals": [cache_signal()],
            "version": 51,
            "last_update": "2026-08-19T17:16:03+00:00",
            "saved_at": "2026-08-19T17:16:03+00:00",
        }
        with patch.object(self.daemon, "CACHE_FILE", fake_path), \
             patch("builtins.open", mock_open(read_data=json.dumps(payload))):
            service._load_cache()
        self.assertEqual(service.signal_version, 51)
        self.assertEqual(service.last_update, payload["last_update"])
        self.assertEqual(service.signals[0]["pair"], "EURUSD")

    def test_refresh_failure_and_empty_refresh_keep_previous_cache(self):
        for outcome in ("empty", "failure"):
            service = self.daemon.SignalService.__new__(self.daemon.SignalService)
            service.service = SimpleNamespace(pairs=["EURUSD"])
            service.signals = [cache_signal()]
            service.signal_version = 7
            service.last_update = "2026-01-01T00:00:00+00:00"
            service.lock = threading.Lock()
            service.total_updates = 0
            service.failed_updates = 0
            service.timeout_count = 0
            service._save_cache = Mock()
            if outcome == "empty":
                service.analyze_pair = lambda pair: None
            else:
                def fail(pair):
                    raise RuntimeError("refresh failure")
                service.analyze_pair = fail
            service.executor = ThreadPoolExecutor(max_workers=1)
            try:
                self.assertTrue(service.update_signals())
            finally:
                service.executor.shutdown(wait=True)
            self.assertEqual(service.signals[0]["pair"], "EURUSD")
            self.assertEqual(service.signal_version, 7)
            # Legacy behavior increments total_updates twice in the same
            # successful update cycle.
            self.assertEqual(service.total_updates, 2)
            service._save_cache.assert_called_once()

    def test_stale_cached_pair_is_still_returned_as_cached(self):
        service = self.daemon.SignalService.__new__(self.daemon.SignalService)
        stale = cache_signal()
        stale["timestamp"] = "2020-01-01T00:00:00+00:00"
        service.signals = [stale]
        service.signal_version = 1
        service.last_update = "2020-01-01T00:00:00+00:00"
        service.lock = threading.Lock()
        self.daemon.signal_service = service
        response = asyncio.run(self.daemon.get_pair_signal("EURUSD"))
        self.assertTrue(response["cached"])
        self.assertEqual(response["signal"]["timestamp"], "2020-01-01T00:00:00+00:00")


class _Model:
    def __init__(self, direction, confidence):
        self.direction = direction
        self.confidence = confidence

    def predict_proba(self, frame):
        return [[1 - self.confidence, self.confidence]] if self.direction == "BUY" else [[self.confidence, 1 - self.confidence]]

    def predict(self, frame):
        return [1 if self.direction == "BUY" else 0]


if __name__ == "__main__":
    unittest.main()
