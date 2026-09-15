"""Phase 3 shadow-adapter parity tests.

These tests deliberately compare direct legacy calls with calls through the
shadow adapters.  The adapters are not allowed to create a live dependency
graph: every dependency used here is explicitly marked shadow-only.
"""

from __future__ import annotations

import copy
import hashlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[2]
CHARACTERIZATION_DIR = ROOT / "tests" / "characterization"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(CHARACTERIZATION_DIR) not in sys.path:
    sys.path.insert(0, str(CHARACTERIZATION_DIR))

from legacy_v3_fixtures import (  # noqa: E402
    configured_signal_trader,
    load_legacy_modules,
    signal_frame,
)
from packages.compatibility.legacy_v3_shadow import (  # noqa: E402
    ShadowBrokerAdapter,
    ShadowDecisionAdapter,
    ShadowEnvironment,
    ShadowExecutionAdapter,
    ShadowPersistenceAdapter,
    ShadowPositionManagementAdapter,
    ShadowRiskAdapter,
    ShadowSignalAdapter,
    ShadowModeViolation,
)


BASELINE_SHA256 = (
    "1A33D16E8CCF6E9532448F23631AA5E34FE5E12864C9CF5A961ACFB525E959BF"
)


class _ShadowHTTP:
    shadow_only = True


class _ShadowRecorder:
    shadow_only = True

    def __init__(self):
        self.calls = []

    def log_trade_entry(self, *args, **kwargs):
        self.calls.append(("entry", args, kwargs))
        return "entry-record"

    def log_trade_exit(self, *args, **kwargs):
        self.calls.append(("exit", args, kwargs))
        return "exit-record"


class _ShadowAccount:
    shadow_only = True

    def __init__(self, broker):
        self.broker = broker


class _SizingBroker:
    shadow_only = True

    def get_balance(self):
        return 10_000.0


def _without_timestamp(value):
    """Remove only the explicitly nondeterministic signal timestamp field."""

    result = copy.deepcopy(value)
    if isinstance(result, dict):
        result.pop("timestamp", None)
    return result


class Phase3ShadowParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signal_module, cls.daemon_module, cls.broker_module, cls.auto_module, cls.mt5 = (
            load_legacy_modules()
        )
        cls.mt5.shadow_only = True

    def test_phase2_baseline_is_immutable(self):
        baseline = ROOT / "tests" / "characterization" / "legacy_v3_baseline.json"
        digest = hashlib.sha256(baseline.read_bytes()).hexdigest().upper()
        self.assertEqual(BASELINE_SHA256, digest)

    def test_signal_adapter_matches_legacy_output(self):
        direct = configured_signal_trader(self.signal_module)
        wrapped = configured_signal_trader(self.signal_module)
        direct.shadow_only = True
        wrapped.shadow_only = True

        expected = direct.get_real_signal("EURUSD")
        actual = ShadowSignalAdapter(wrapped).get_real_signal("EURUSD")

        # Timestamp is the only field intentionally excluded; the comparison
        # rule is explicit because the legacy method creates it at call time.
        self.assertEqual(_without_timestamp(expected), _without_timestamp(actual))

    def test_signal_error_is_propagated_unchanged(self):
        source = types.SimpleNamespace(shadow_only=True)
        source.get_real_signal = Mock(side_effect=ValueError("legacy signal failure"))
        adapter = ShadowSignalAdapter(source)
        with self.assertRaisesRegex(ValueError, "legacy signal failure"):
            adapter.get_real_signal("EURUSD")
        source.get_real_signal.assert_called_once_with("EURUSD")

    def test_decision_helpers_delegate_without_rule_changes(self):
        legacy = self.auto_module.AutoTrader.__new__(self.auto_module.AutoTrader)
        legacy.shadow_only = True
        legacy.session_hours = {"EURUSD": [[0, 24]]}
        legacy.positions = []
        adapter = ShadowDecisionAdapter(legacy)

        self.assertEqual(
            legacy.is_in_session("EURUSD"), adapter.is_in_session("EURUSD")
        )
        self.assertEqual(
            legacy.position_exists("EURUSD", "BUY", []),
            adapter.position_exists("EURUSD", "BUY", []),
        )
        self.assertEqual(
            legacy.has_opposite("EURUSD", "BUY", []),
            adapter.has_opposite("EURUSD", "BUY", []),
        )

    def test_risk_and_sizing_delegate_exactly(self):
        legacy = self.auto_module.AutoTrader.__new__(self.auto_module.AutoTrader)
        legacy.shadow_only = True
        account = types.SimpleNamespace(broker=_SizingBroker())

        expected = legacy.calc_position_size(account, "EURUSD", 1.1000, 1.0975, 0.01)
        actual = ShadowRiskAdapter(legacy).calc_position_size(
            account, "EURUSD", 1.1000, 1.0975, 0.01
        )
        self.assertEqual(expected, actual)

    def test_broker_request_matches_legacy_and_remains_pending_without_initial_stops(self):
        direct_broker = self.broker_module.MT5Broker.__new__(self.broker_module.MT5Broker)
        wrapped_broker = self.broker_module.MT5Broker.__new__(self.broker_module.MT5Broker)
        direct_broker.shadow_only = True
        wrapped_broker.shadow_only = True
        direct_broker.connected = True
        wrapped_broker.connected = True

        self.mt5.requests.clear()
        expected = direct_broker.place_market_order(
            "EURUSDm", "BUY", 1.10007, 1.0975, 1.1040, 0.83, volume=0.12
        )
        expected_request = copy.deepcopy(self.mt5.requests[-1])

        self.mt5.requests.clear()
        environment = ShadowEnvironment(self.mt5, _ShadowHTTP())
        actual = ShadowBrokerAdapter(wrapped_broker, environment).place_market_order(
            "EURUSDm", "BUY", 1.10007, 1.0975, 1.1040, 0.83, volume=0.12
        )
        actual_request = copy.deepcopy(self.mt5.requests[-1])

        self.assertEqual(expected, actual)
        self.assertEqual(expected_request, actual_request)
        self.assertEqual(self.mt5.ORDER_TYPE_BUY_LIMIT, actual_request["type"])
        self.assertNotIn("sl", actual_request)
        self.assertNotIn("tp", actual_request)

    def test_broker_rejection_and_error_result_are_delegated(self):
        direct_broker = self.broker_module.MT5Broker.__new__(self.broker_module.MT5Broker)
        wrapped_broker = self.broker_module.MT5Broker.__new__(self.broker_module.MT5Broker)
        direct_broker.shadow_only = True
        wrapped_broker.shadow_only = True
        direct_broker.connected = True
        wrapped_broker.connected = True
        from types import SimpleNamespace

        self.mt5.order_results = [
            SimpleNamespace(retcode=10019, order=0, comment="no money")
        ]
        expected = direct_broker.place_market_order(
            "EURUSDm", "BUY", 1.10007, 1.0975, 1.1040, 0.83, volume=0.12
        )
        self.mt5.order_results = [
            SimpleNamespace(retcode=10019, order=0, comment="no money")
        ]
        actual = ShadowBrokerAdapter(
            wrapped_broker, ShadowEnvironment(self.mt5, _ShadowHTTP())
        ).place_market_order(
            "EURUSDm", "BUY", 1.10007, 1.0975, 1.1040, 0.83, volume=0.12
        )
        self.assertEqual(expected, actual)

    def test_persistence_payload_is_delegated_unchanged(self):
        direct = _ShadowRecorder()
        wrapped = _ShadowRecorder()
        payload = {
            "account": "Demo2",
            "pair": "EURUSD",
            "direction": "BUY",
            "volume": 0.8,
            "planned_price": 1.15123,
            "ticket": 123456,
        }

        expected = direct.log_trade_entry(payload)
        actual = ShadowPersistenceAdapter(wrapped).log_trade_entry(payload)

        self.assertEqual(expected, actual)
        self.assertEqual(direct.calls, wrapped.calls)

    def test_execution_adapter_requires_shadow_account_and_delegates(self):
        legacy = Mock()
        legacy.shadow_only = True
        legacy.manage_account.return_value = {"accepted": False, "reason": "session"}
        broker = types.SimpleNamespace(shadow_only=True)
        account = _ShadowAccount(broker)
        adapter = ShadowExecutionAdapter(
            legacy, ShadowEnvironment(self.mt5, _ShadowHTTP())
        )

        expected = legacy.manage_account(account)
        legacy.manage_account.reset_mock()
        actual = adapter.manage_account(account)

        self.assertEqual(expected, actual)
        legacy.manage_account.assert_called_once_with(account)

    def test_position_management_calls_are_delegated(self):
        legacy = Mock()
        legacy.shadow_only = True
        legacy.apply_atr_trailing_stop.return_value = "trail-result"
        legacy.apply_time_exit.return_value = "time-result"
        adapter = ShadowPositionManagementAdapter(
            legacy, ShadowEnvironment(self.mt5, _ShadowHTTP())
        )
        args = ("account", "EURUSD", 0.001, "BUY", 1.1, {"ticket": 7})

        self.assertEqual(
            legacy.apply_atr_trailing_stop(*args),
            adapter.apply_atr_trailing_stop(*args),
        )
        self.assertEqual(
            legacy.apply_time_exit("account", "EURUSD", {"ticket": 7}),
            adapter.apply_time_exit("account", "EURUSD", {"ticket": 7}),
        )

    def test_live_dependencies_are_rejected(self):
        with self.assertRaises(ShadowModeViolation):
            ShadowEnvironment(self.mt5, types.SimpleNamespace(shadow_only=False))

        unsafe = types.SimpleNamespace(shadow_only=False)
        with self.assertRaises(ShadowModeViolation):
            ShadowSignalAdapter(unsafe)


if __name__ == "__main__":
    unittest.main()
