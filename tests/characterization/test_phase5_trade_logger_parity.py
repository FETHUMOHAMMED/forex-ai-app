"""Offline characterization of the legacy SQLite TradeLogger boundary."""

from __future__ import annotations

import sqlite3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import risk.trade_logger as legacy_trade_logger  # noqa: E402
from risk.trade_logger import TradeLogger  # noqa: E402


def _signal(pair="EURUSD", direction="BUY"):
    return {
        "pair": pair,
        "signal": direction,
        "confidence": 0.83,
        "entry": 1.15123,
        "stop_loss": 1.15299,
        "take_profit": 1.14842,
        "institutional_bias": "BREAKOUT",
        "institutional_score": 81.85,
        "dealer_pressure": "SELLING_PRESSURE",
        "liquidity_state": "SWEEP_SELL",
        "continuation_prob": 0.5,
    }


class LegacyTradeLoggerCharacterization(unittest.TestCase):
    def setUp(self):
        self.logger = TradeLogger(db_path=":memory:")

    def tearDown(self):
        self.logger.conn.close()

    def test_schema_and_indexes_are_created_with_legacy_columns(self):
        columns = [row[1] for row in self.logger.conn.execute("PRAGMA table_info(trades)")]
        indexes = {
            row[1] for row in self.logger.conn.execute("PRAGMA index_list(trades)")
        }

        self.assertEqual(columns[:14], [
            "id", "timestamp", "pair", "signal", "confidence", "entry",
            "stop_loss", "take_profit", "exit_price", "exit_time", "pnl",
            "pnl_percent", "result", "volume",
        ])
        for column in (
            "ticket", "regime", "reason", "account", "institutional_bias",
            "institutional_score", "dealer_pressure", "liquidity_state",
            "continuation_prob",
        ):
            self.assertIn(column, columns)
        for index in ("idx_ticket", "idx_pair", "idx_exit_time", "idx_account", "idx_regime"):
            self.assertIn(index, indexes)

    def test_entry_payload_and_dynamic_timestamp_match_legacy_schema(self):
        before = datetime.now()
        row_id = self.logger.log_trade_entry(
            _signal(), volume=0.12, ticket=987, regime="volatile", account="Live_Micro"
        )
        after = datetime.now()

        self.assertEqual(row_id, 1)
        row = self.logger.conn.execute(
            "SELECT timestamp, pair, signal, confidence, entry, stop_loss, take_profit, "
            "volume, ticket, regime, account, institutional_bias, institutional_score, "
            "dealer_pressure, liquidity_state, continuation_prob FROM trades WHERE id=?",
            (row_id,),
        ).fetchone()
        timestamp = datetime.fromisoformat(row[0])
        self.assertTrue(before <= timestamp <= after)
        self.assertEqual(row[1:], (
            "EURUSD", "BUY", 0.83, 1.15123, 1.15299, 1.14842,
            0.12, 987, "volatile", "Live_Micro", "BREAKOUT", 81.85,
            "SELLING_PRESSURE", "SWEEP_SELL", 0.5,
        ))

    def test_missing_signal_metadata_uses_legacy_defaults(self):
        signal = {
            "pair": "GBPUSD", "signal": "SELL", "confidence": 0.51,
            "entry": 1.25, "stop_loss": 1.252, "take_profit": 1.246,
        }
        self.logger.log_trade_entry(signal)
        row = self.logger.conn.execute(
            "SELECT institutional_bias, institutional_score, dealer_pressure, "
            "liquidity_state, continuation_prob FROM trades"
        ).fetchone()
        self.assertEqual(row, ("NEUTRAL", 0.0, "NEUTRAL", "NO_EVENT", 0.50))

    def test_exit_update_calculates_legacy_result_and_pnl_percent(self):
        self.logger.log_trade_entry(
            _signal(), volume=0.12, ticket=987, regime="volatile", account="Live_Micro"
        )
        exit_time = datetime(2026, 8, 13, tzinfo=timezone.utc)
        self.logger.log_trade_exit(
            ticket=987, exit_price=1.15, exit_time=exit_time, pnl=2.5, reason="closed"
        )
        row = self.logger.conn.execute(
            "SELECT exit_price, exit_time, pnl, pnl_percent, result, reason "
            "FROM trades WHERE ticket=987"
        ).fetchone()
        self.assertEqual(row[0], 1.15)
        self.assertEqual(row[1], "2026-08-13T00:00:00+00:00")
        self.assertEqual(row[2], 2.5)
        self.assertAlmostEqual(row[3], (2.5 / 1.15123) * 100.0)
        self.assertEqual(row[4:], ("WIN", "closed"))

    def test_exit_result_labels_preserve_loss_and_zero_behavior(self):
        for ticket, pnl, result in ((1001, -1.0, "LOSS"), (1002, 0.0, "")):
            self.logger.log_trade_entry(_signal(), ticket=ticket)
            self.logger.log_trade_exit(
                ticket=ticket,
                exit_price=1.15,
                exit_time=datetime.now(timezone.utc),
                pnl=pnl,
                reason="closed",
            )
            actual = self.logger.conn.execute(
                "SELECT result FROM trades WHERE ticket=?", (ticket,)
            ).fetchone()[0]
            self.assertEqual(actual, result)

    def test_missing_exit_ticket_is_a_noop(self):
        self.logger.log_trade_entry(_signal(), ticket=987)
        self.logger.log_trade_exit(
            ticket=404,
            exit_price=1.15,
            exit_time=datetime.now(timezone.utc),
            pnl=2.5,
            reason="missing",
        )
        row = self.logger.conn.execute(
            "SELECT exit_price, exit_time, pnl, result, reason FROM trades WHERE ticket=987"
        ).fetchone()
        self.assertEqual(row, (None, None, None, None, None))

    def test_recent_trade_queries_preserve_legacy_shapes_and_math(self):
        now = datetime.now(timezone.utc)
        cases = (
            (1, "EURUSD", "BUY", "volatile", 2.5, "Live_Micro", now - timedelta(minutes=3)),
            (2, "EURUSD", "BUY", "volatile", -1.0, "Live_Micro", now - timedelta(minutes=2)),
            (3, "GBPUSD", "SELL", "ranging", 1.0, "Demo2", now - timedelta(minutes=1)),
        )
        for ticket, pair, direction, regime, pnl, account, exit_time in cases:
            self.logger.log_trade_entry(
                _signal(pair, direction), ticket=ticket, regime=regime, account=account
            )
            self.logger.log_trade_exit(ticket, 1.15, exit_time, pnl, "closed")

        self.assertEqual(self.logger.get_recent_pnls(limit=2), [1.0, -1.0])
        self.assertEqual(self.logger.get_recent_trade_stats(days=30), (3, 2, 2 / 3 * 100))
        self.assertEqual(
            self.logger.get_recent_trade_stats(days=30, account="Live_Micro"),
            (2, 1, 50.0),
        )
        regimes = self.logger.get_regime_performance(days=30)
        self.assertEqual(regimes["volatile"]["trades"], 2)
        self.assertEqual(regimes["volatile"]["wins"], 1)
        self.assertEqual(regimes["volatile"]["gross_profit"], 2.5)
        self.assertEqual(regimes["volatile"]["gross_loss"], 1.0)
        self.assertEqual(regimes["volatile"]["win_rate"], 0.5)
        self.assertEqual(regimes["volatile"]["profit_factor"], 2.5)

        pairs = self.logger.get_pair_performance(days=30)
        self.assertEqual(pairs["EURUSD"]["trades"], 2)
        self.assertEqual(pairs["EURUSD"]["wins"], 1)
        self.assertEqual(pairs["GBPUSD"]["profit_factor"], 5.0)

    def test_daily_and_aggregate_performance_shapes_are_preserved(self):
        self.logger.log_trade_entry(_signal(), ticket=777, account="Live_Micro")
        self.logger.log_trade_exit(
            777, 1.15, datetime.now(timezone.utc), 2.5, "closed"
        )
        today = datetime.now().strftime("%Y-%m-%d")
        daily = self.logger.get_daily_stats(today)
        self.assertEqual(daily["date"], today)
        self.assertEqual(daily["total_trades"], 1)
        self.assertEqual(daily["winning_trades"], 1)
        self.assertEqual(daily["total_pnl"], 2.5)
        self.assertEqual(daily["win_rate"], 100.0)

        stats = self.logger.get_performance_stats()
        self.assertEqual(stats["total_trades"], 1)
        self.assertEqual(stats["winning_trades"], 1)
        self.assertEqual(stats["losing_trades"], 0)
        self.assertEqual(stats["win_rate"], "100.0%")
        self.assertEqual(stats["total_pnl"], "$2.50")
        self.assertEqual(stats["avg_confidence"], "83.0%")
        self.assertEqual(stats["best_trade"], "$2.50")
        self.assertEqual(stats["worst_trade"], "$2.50")

    def test_existing_partial_schema_is_migrated_and_second_start_is_idempotent(self):
        self.logger.conn.close()
        raw = sqlite3.connect(":memory:")
        raw.execute("CREATE TABLE trades (id INTEGER PRIMARY KEY, timestamp TEXT, pair TEXT)")
        raw.commit()

        # The legacy constructor accepts a path, but this test supplies an
        # already-created isolated in-memory connection so no file is needed.
        with patch.object(legacy_trade_logger.sqlite3, "connect", return_value=raw):
            first = TradeLogger(db_path="isolated-partial-schema")
            first_columns = {
                row[1] for row in first.conn.execute("PRAGMA table_info(trades)")
            }
            second = TradeLogger(db_path="isolated-partial-schema")
            second_columns = {
                row[1] for row in second.conn.execute("PRAGMA table_info(trades)")
            }
        raw.close()
        self.logger = TradeLogger(db_path=":memory:")

        # Legacy migration adds only its explicit optional columns; it does
        # not reconstruct missing base columns such as confidence.
        self.assertTrue({"id", "timestamp", "pair", "ticket", "account", "regime"}.issubset(first_columns))
        self.assertNotIn("confidence", first_columns)
        self.assertEqual(first_columns, second_columns)

    def test_closed_connection_preserves_legacy_error_handling_split(self):
        self.logger.conn.close()
        with self.assertRaises(sqlite3.ProgrammingError):
            self.logger.get_recent_pnls()

        # log_trade_exit catches its own database error and returns None.
        with patch("builtins.print") as print_mock:
            self.assertIsNone(
                self.logger.log_trade_exit(
                    ticket=404,
                    exit_price=1.15,
                    exit_time=datetime.now(timezone.utc),
                    pnl=1.0,
                    reason="closed",
                )
            )
        print_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
