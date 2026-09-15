"""Offline parity tests for the Phase 6 TradeLogger shadow adapter."""

from __future__ import annotations

import hashlib
import sqlite3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.compatibility.legacy_trade_logger_shadow import (  # noqa: E402
    ShadowTradeLoggerAdapter,
)
from packages.compatibility.legacy_v3_shadow import ShadowModeViolation  # noqa: E402
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


def _row_without_dynamic_timestamp(logger, ticket):
    return logger.conn.execute(
        "SELECT pair, signal, confidence, entry, stop_loss, take_profit, exit_price, "
        "exit_time, pnl, pnl_percent, result, volume, ticket, regime, reason, account "
        "FROM trades WHERE ticket=?",
        (ticket,),
    ).fetchone()


class Phase6TradeLoggerShadowParityTests(unittest.TestCase):
    def test_phase2_baseline_remains_immutable(self):
        baseline = ROOT / "tests" / "characterization" / "legacy_v3_baseline.json"
        self.assertEqual(
            hashlib.sha256(baseline.read_bytes()).hexdigest().upper(), BASELINE_SHA256
        )

    def test_entry_and_exit_rows_match_legacy_exactly(self):
        direct = _logger()
        wrapped = _logger()
        adapter = ShadowTradeLoggerAdapter(wrapped)
        signal = _signal()
        exit_time = datetime(2026, 8, 13, tzinfo=timezone.utc)

        direct_id = direct.log_trade_entry(
            signal, volume=0.12, ticket=987, regime="volatile", account="Live_Micro"
        )
        wrapped_id = adapter.log_trade_entry(
            signal, volume=0.12, ticket=987, regime="volatile", account="Live_Micro"
        )
        self.assertEqual(direct_id, wrapped_id)

        direct.log_trade_exit(987, 1.15, exit_time, 2.5, "closed")
        adapter.log_trade_exit(987, 1.15, exit_time, 2.5, "closed")
        self.assertEqual(
            _row_without_dynamic_timestamp(direct, 987),
            _row_without_dynamic_timestamp(wrapped, 987),
        )

        direct.conn.close()
        wrapped.conn.close()

    def test_query_outputs_match_for_identical_in_memory_fixtures(self):
        direct = _logger()
        wrapped = _logger()
        adapter = ShadowTradeLoggerAdapter(wrapped)
        now = datetime.now(timezone.utc)
        cases = (
            (1, "EURUSD", "BUY", "volatile", 2.5, "Live_Micro", now - timedelta(minutes=3)),
            (2, "EURUSD", "BUY", "volatile", -1.0, "Live_Micro", now - timedelta(minutes=2)),
            (3, "GBPUSD", "SELL", "ranging", 1.0, "Demo2", now - timedelta(minutes=1)),
        )
        for ticket, pair, direction, regime, pnl, account, exit_time in cases:
            args = (_signal(pair, direction),)
            kwargs = {"ticket": ticket, "regime": regime, "account": account}
            direct.log_trade_entry(*args, **kwargs)
            adapter.log_trade_entry(*args, **kwargs)
            direct.log_trade_exit(ticket, 1.15, exit_time, pnl, "closed")
            adapter.log_trade_exit(ticket, 1.15, exit_time, pnl, "closed")

        today = datetime.now().strftime("%Y-%m-%d")
        comparisons = (
            (direct.get_recent_pnls(limit=2), adapter.get_recent_pnls(limit=2)),
            (direct.get_recent_trade_stats(days=30), adapter.get_recent_trade_stats(days=30)),
            (
                direct.get_recent_trade_stats(days=30, account="Live_Micro"),
                adapter.get_recent_trade_stats(days=30, account="Live_Micro"),
            ),
            (direct.get_regime_performance(days=30), adapter.get_regime_performance(days=30)),
            (direct.get_pair_performance(days=30), adapter.get_pair_performance(days=30)),
            (direct.get_daily_stats(today), adapter.get_daily_stats(today)),
            (direct.get_performance_stats(), adapter.get_performance_stats()),
        )
        for expected, actual in comparisons:
            self.assertEqual(expected, actual)

        direct.conn.close()
        wrapped.conn.close()

    def test_legacy_noop_and_error_behavior_are_delegated(self):
        direct = _logger()
        wrapped = _logger()
        adapter = ShadowTradeLoggerAdapter(wrapped)
        signal = _signal()
        direct.log_trade_entry(signal, ticket=987)
        adapter.log_trade_entry(signal, ticket=987)

        direct_result = direct.log_trade_exit(
            404, 1.15, datetime.now(timezone.utc), 2.5, "missing"
        )
        actual_result = adapter.log_trade_exit(
            404, 1.15, datetime.now(timezone.utc), 2.5, "missing"
        )
        self.assertEqual(direct_result, actual_result)
        self.assertEqual(
            _row_without_dynamic_timestamp(direct, 987),
            _row_without_dynamic_timestamp(wrapped, 987),
        )

        direct.conn.close()
        wrapped.conn.close()
        with self.assertRaises(sqlite3.ProgrammingError):
            direct.get_recent_pnls()
        with self.assertRaises(sqlite3.ProgrammingError):
            adapter.get_recent_pnls()

    def test_unmarked_or_file_backed_loggers_are_rejected(self):
        with self.assertRaises(ShadowModeViolation):
            ShadowTradeLoggerAdapter(SimpleNamespace(conn=sqlite3.connect(":memory:")))

        file_like = SimpleNamespace(
            shadow_only=True,
            conn=SimpleNamespace(
                execute=lambda _sql: SimpleNamespace(
                    fetchall=lambda: [(0, "main", "C:/production/trades.db")]
                )
            ),
        )
        with self.assertRaises(ShadowModeViolation):
            ShadowTradeLoggerAdapter(file_like)


if __name__ == "__main__":
    unittest.main()
