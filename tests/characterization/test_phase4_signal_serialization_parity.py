"""Offline Phase 4 parity tests for the legacy V3 signal HTTP boundary."""

from __future__ import annotations

import asyncio
import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import HTTPException
from starlette.responses import JSONResponse


ROOT = Path(__file__).resolve().parents[2]
CHARACTERIZATION_DIR = ROOT / "tests" / "characterization"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(CHARACTERIZATION_DIR) not in sys.path:
    sys.path.insert(0, str(CHARACTERIZATION_DIR))

from legacy_v3_fixtures import cache_signal, load_legacy_modules  # noqa: E402
from packages.compatibility.legacy_v3_shadow import (  # noqa: E402
    ShadowModeViolation,
    ShadowSignalSerializationAdapter,
)


class _MarkedEndpoint:
    shadow_only = True

    def __init__(self, endpoint):
        self.endpoint = endpoint

    async def __call__(self, pair):
        return await self.endpoint(pair)


class _OfflineSignalService:
    def __init__(self, signals=None, analyze=None):
        self.signals = list(signals or [])
        self.signal_version = 51
        self.last_update = "2026-08-19T17:16:03+00:00"
        self.analyze_calls = []
        self.analyze = analyze or (lambda pair: None)

    def get_signals(self):
        return list(self.signals), self.signal_version

    def analyze_pair(self, pair):
        self.analyze_calls.append(pair)
        return self.analyze(pair)


async def _legacy_http_response(endpoint, pair):
    """Model the framework response around the unchanged legacy endpoint."""

    try:
        content = await endpoint(pair)
        return JSONResponse(content=content, status_code=200)
    except HTTPException as exc:
        return JSONResponse(
            content={"detail": exc.detail},
            status_code=exc.status_code,
            headers=exc.headers,
        )


class Phase4SignalSerializationParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signal_module, cls.daemon_module, _broker, _execution, cls.mt5 = (
            load_legacy_modules()
        )
        cls.mt5.shadow_only = True
        cls.endpoint = _MarkedEndpoint(cls.daemon_module.get_pair_signal)

    def setUp(self):
        self.service = _OfflineSignalService()
        self.daemon_module.signal_service = self.service
        self.adapter = ShadowSignalSerializationAdapter(self.endpoint)

    def _compare_legacy_and_shadow(self, pair, exact_body=True):
        expected = asyncio.run(_legacy_http_response(self.endpoint, pair))
        actual = asyncio.run(self.adapter.get_pair_signal(pair))
        self.assertEqual(expected.status_code, actual.status_code)
        if exact_body:
            self.assertEqual(expected.body, actual.body)
        self.assertEqual(expected.media_type, actual.media_type)
        return expected, actual

    def test_cached_buy_response_matches_exactly(self):
        self.service.signals = [cache_signal("EURUSD", "BUY", 0.83)]
        expected, actual = self._compare_legacy_and_shadow("EURUSD")

        self.assertEqual(expected.body, actual.body)
        payload = json.loads(actual.body)
        self.assertEqual(set(payload), {"signal", "cached"})
        self.assertTrue(payload["cached"])
        self.assertEqual(payload["signal"]["signal"], "BUY")
        self.assertEqual(payload["signal"]["confidence"], 0.83)
        self.assertEqual(payload["signal"]["entry"], 1.15123)
        self.assertEqual(payload["signal"]["stop_loss"], 1.15299)
        self.assertEqual(payload["signal"]["take_profit"], 1.14842)
        self.assertEqual(payload["signal"]["pair"], "EURUSD")

    def test_cached_sell_response_matches_exactly(self):
        self.service.signals = [cache_signal("EURUSD", "SELL", 0.71)]
        _expected, actual = self._compare_legacy_and_shadow("eurusd")
        payload = json.loads(actual.body)
        self.assertTrue(payload["cached"])
        self.assertEqual(payload["signal"]["signal"], "SELL")
        self.assertEqual(payload["signal"]["confidence"], 0.71)

    def test_missing_pair_is_fresh_no_signal_with_exact_null_shape(self):
        self.service.analyze = lambda pair: None
        _expected, actual = self._compare_legacy_and_shadow("GBPUSD")

        self.assertEqual(actual.status_code, 200)
        self.assertEqual(json.loads(actual.body), {"signal": None, "cached": False})
        self.assertEqual(self.service.analyze_calls, ["GBPUSD", "GBPUSD"])

    def test_invalid_pair_is_not_validated_by_legacy_endpoint(self):
        self.service.analyze = lambda pair: None
        _expected, actual = self._compare_legacy_and_shadow("not-a-pair")

        self.assertEqual(actual.status_code, 200)
        self.assertEqual(json.loads(actual.body), {"signal": None, "cached": False})
        self.assertEqual(self.service.analyze_calls, ["NOT-A-PAIR", "NOT-A-PAIR"])

    def test_signal_generation_failure_becomes_legacy_http_500(self):
        self.service.analyze = Mock(side_effect=RuntimeError("legacy signal failure"))
        expected, actual = self._compare_legacy_and_shadow("EURUSD")

        self.assertEqual(expected.status_code, 500)
        self.assertEqual(actual.status_code, 500)
        self.assertEqual(json.loads(actual.body), {"detail": "legacy signal failure"})

    def test_uninitialized_service_is_legacy_http_503(self):
        self.daemon_module.signal_service = None
        expected, actual = self._compare_legacy_and_shadow("EURUSD")

        self.assertEqual(expected.status_code, 503)
        self.assertEqual(actual.status_code, 503)
        self.assertEqual(json.loads(actual.body), {"detail": "Service not initialized"})

    def test_serialization_failure_is_propagated(self):
        bad_signal = {"pair": "EURUSD", "signal": object()}
        self.service.signals = [bad_signal]

        with self.assertRaises((TypeError, ValueError)):
            asyncio.run(self.adapter.get_pair_signal("EURUSD"))

    def test_dynamic_signal_timestamp_excludes_only_that_field(self):
        calls = 0

        def dynamic_signal(pair):
            nonlocal calls
            calls += 1
            signal = cache_signal(pair=pair)
            signal["timestamp"] = f"2026-08-21T00:00:0{calls}+00:00"
            return signal

        self.service.analyze = dynamic_signal
        expected, actual = self._compare_legacy_and_shadow("EURUSD", exact_body=False)
        expected_payload = json.loads(expected.body)
        actual_payload = json.loads(actual.body)

        self.assertEqual(expected_payload["signal"]["timestamp"], "2026-08-21T00:00:01+00:00")
        self.assertEqual(actual_payload["signal"]["timestamp"], "2026-08-21T00:00:02+00:00")
        expected_payload["signal"].pop("timestamp")
        actual_payload["signal"].pop("timestamp")
        self.assertEqual(expected_payload, actual_payload)

    def test_stale_cached_signal_is_returned_without_expiry_rejection(self):
        stale = cache_signal()
        stale["timestamp"] = "2020-01-01T00:00:00+00:00"
        self.service.signals = [stale]
        self.service.analyze = Mock(side_effect=AssertionError("refresh must not run"))
        _expected, actual = self._compare_legacy_and_shadow("EURUSD")

        payload = json.loads(actual.body)
        self.assertTrue(payload["cached"])
        self.assertEqual(payload["signal"]["timestamp"], "2020-01-01T00:00:00+00:00")
        self.service.analyze.assert_not_called()

    def test_endpoint_does_not_write_or_change_cache_state(self):
        cached = cache_signal()
        self.service.signals = [cached]
        before = copy.deepcopy(self.service.signals)
        self._compare_legacy_and_shadow("EURUSD")
        self.assertEqual(self.service.signals, before)
        self.assertEqual(self.service.analyze_calls, [])

    def test_non_shadow_endpoint_is_rejected(self):
        unsafe = SimpleNamespace(shadow_only=False)
        with self.assertRaises(ShadowModeViolation):
            ShadowSignalSerializationAdapter(unsafe)


if __name__ == "__main__":
    unittest.main()
