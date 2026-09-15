"""Phase 7 tests for the backend-neutral canonical persistence contract."""

from __future__ import annotations

import hashlib
import sqlite3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.compatibility.canonical_trade_logger_contract import (  # noqa: E402
    CanonicalTradeLoggerContract,
    FUTURE_IMPROVEMENTS,
    LEGACY_QUIRKS,
    REQUIRED_COMPATIBILITY_BEHAVIORS,
)
from packages.compatibility.legacy_trade_logger_shadow import (  # noqa: E402
    ShadowTradeLoggerAdapter,
)
from risk.trade_logger import TradeLogger  # noqa: E402


BASELINE_SHA256 = (
    "1A33D16E8CCF6E9532448F23631AA5E34FE5E12864C9CF5A961ACFB525E959BF"
)


def _signal(pair="EURUSD", direction="BUY", confidence=0.83):
    return {
        "pair": pair,
        "signal": direction,
        "confidence": confidence,
        "entry": 1.15123,
        "stop_loss": 1.15299,
        "take_profit": 1.14842,
        "institutional_bias": "BREAKOUT",
        "institutional_score": 81.85,
        "dealer_pressure": "SELLING_PRESSURE",
        "liquidity_state": "SWEEP_SELL",
        "continuation_prob": 0.5,
    }


def _logger():
    value = TradeLogger(db_path=":memory:")
    value.shadow_only = True
    return value


def _row_without_timestamp(logger, ticket):
    return logger.conn.execute(
        "SELECT pair, signal, confidence, entry, stop_loss, take_profit, exit_price, "
        "exit_time, pnl, pnl_percent, result, volume, ticket, regime, reason, account "
        "FROM trades WHERE ticket=?",
        (ticket,),
    ).fetchone()


class Phase7CanonicalTradeLoggerParityTests(unittest.TestCase):
    def test_baseline_is_unchanged(self):
        baseline = ROOT / "tests" / "characterization" / "legacy_v3_baseline.json"
        self.assertEqual(
            hashlib.sha256(baseline.read_bytes()).hexdigest().upper(), BASELINE_SHA256
        )

    def test_contract_has_all_required_methods_and_legacy_implements_it(self):
        required = {
            "log_trade_entry", "log_trade_exit", "get_recent_pnls",
            "get_recent_trade_stats", "get_regime_performance",
            "get_pair_performance", "get_daily_stats", "get_performance_stats",
        }
        self.assertTrue(required.issubset(set(dir(CanonicalTradeLoggerContract))))
        logger = _logger()
        adapter = ShadowTradeLoggerAdapter(logger)
        self.assertIsInstance(logger, CanonicalTradeLoggerContract)
        self.assertIsInstance(adapter, CanonicalTradeLoggerContract)
        logger.conn.close()

    def test_contract_clauses_explicitly_separate_compatibility_quirks_and_future_work(self):
        self.assertTrue(REQUIRED_COMPATIBILITY_BEHAVIORS)
        self.assertTrue(LEGACY_QUIRKS)
        self.assertTrue(FUTURE_IMPROVEMENTS)
        self.assertTrue(any("partial-schema" in item for item in LEGACY_QUIRKS))
        self.assertTrue(any("pnl_percent" in item for item in LEGACY_QUIRKS))
        self.assertTrue(any("timezone-aware" in item for item in FUTURE_IMPROVEMENTS))

    def test_entry_and_exit_contract_parity(self):
        direct = _logger()
        wrapped_logger = _logger()
        contract: CanonicalTradeLoggerContract = ShadowTradeLoggerAdapter(wrapped_logger)
        exit_time = datetime(2026, 8, 13, tzinfo=timezone.utc)

        direct_id = direct.log_trade_entry(
            _signal(), volume=0.12, ticket=987, regime="volatile", account="Live_Micro"
        )
        contract_id = contract.log_trade_entry(
            _signal(), volume=0.12, ticket=987, regime="volatile", account="Live_Micro"
        )
        self.assertEqual(direct_id, contract_id)

        self.assertIsNone(direct.log_trade_exit(987, 1.15, exit_time, 2.5, "closed"))
        self.assertIsNone(contract.log_trade_exit(987, 1.15, exit_time, 2.5, "closed"))
        self.assertEqual(
            _row_without_timestamp(direct, 987),
            _row_without_timestamp(wrapped_logger, 987),
        )
        direct.conn.close()
        wrapped_logger.conn.close()

    def test_query_contract_parity(self):
        direct = _logger()
        wrapped_logger = _logger()
        contract: CanonicalTradeLoggerContract = ShadowTradeLoggerAdapter(wrapped_logger)
        now = datetime.now(timezone.utc)
        cases = (
            (1, "EURUSD", "BUY", "volatile", 2.5, "Live_Micro", now - timedelta(minutes=3)),
            (2, "EURUSD", "BUY", "volatile", -1.0, "Live_Micro", now - timedelta(minutes=2)),
            (3, "GBPUSD", "SELL", "ranging", 1.0, "Demo2", now - timedelta(minutes=1)),
        )
        for ticket, pair, direction, regime, pnl, account, exit_time in cases:
            kwargs = {"ticket": ticket, "regime": regime, "account": account}
            direct.log_trade_entry(_signal(pair, direction), **kwargs)
            contract.log_trade_entry(_signal(pair, direction), **kwargs)
            direct.log_trade_exit(ticket, 1.15, exit_time, pnl, "closed")
            contract.log_trade_exit(ticket, 1.15, exit_time, pnl, "closed")

        today = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(direct.get_recent_pnls(2), contract.get_recent_pnls(2))
        self.assertEqual(
            direct.get_recent_trade_stats(30), contract.get_recent_trade_stats(30)
        )
        self.assertEqual(
            direct.get_recent_trade_stats(30, "Live_Micro"),
            contract.get_recent_trade_stats(30, "Live_Micro"),
        )
        self.assertEqual(
            direct.get_regime_performance(30), contract.get_regime_performance(30)
        )
        self.assertEqual(
            direct.get_pair_performance(30), contract.get_pair_performance(30)
        )
        self.assertEqual(direct.get_daily_stats(today), contract.get_daily_stats(today))
        self.assertEqual(direct.get_performance_stats(), contract.get_performance_stats())
        direct.conn.close()
        wrapped_logger.conn.close()

    def test_noop_and_query_error_semantics_remain_legacy_compatible(self):
        direct = _logger()
        wrapped_logger = _logger()
        contract: CanonicalTradeLoggerContract = ShadowTradeLoggerAdapter(wrapped_logger)
        direct.log_trade_entry(_signal(), ticket=987)
        contract.log_trade_entry(_signal(), ticket=987)

        self.assertIsNone(direct.log_trade_exit(404, 1.15, datetime.now(timezone.utc), 1.0))
        self.assertIsNone(contract.log_trade_exit(404, 1.15, datetime.now(timezone.utc), 1.0))
        self.assertEqual(_row_without_timestamp(direct, 987), _row_without_timestamp(wrapped_logger, 987))

        direct.conn.close()
        wrapped_logger.conn.close()
        with self.assertRaises(sqlite3.ProgrammingError):
            direct.get_recent_pnls()
        with self.assertRaises(sqlite3.ProgrammingError):
            contract.get_recent_pnls()


if __name__ == "__main__":
    unittest.main()
