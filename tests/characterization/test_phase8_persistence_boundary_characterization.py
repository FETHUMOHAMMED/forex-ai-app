"""Phase 8A characterization of the complete legacy persistence boundary.

These tests intentionally assert legacy behavior. They use only in-memory
SQLite and never construct an MT5, broker, network, cache, or production DB
dependency.
"""

import sqlite3
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import risk.trade_logger as legacy_trade_logger
from risk.trade_logger import TradeLogger


def _signal(pair="EURUSD", entry=1.1000):
    return {
        "pair": pair,
        "signal": "BUY",
        "confidence": 0.83,
        "entry": entry,
        "stop_loss": entry - 0.0020,
        "take_profit": entry + 0.0040,
        "institutional_bias": "BREAKOUT",
        "institutional_score": 81.85,
        "dealer_pressure": "BUYING_PRESSURE",
        "liquidity_state": "SWEEP_BUY",
        "continuation_prob": 0.50,
    }


class Phase8PersistenceBoundaryCharacterization(unittest.TestCase):
    def setUp(self):
        self.logger = TradeLogger(db_path=":memory:")

    def tearDown(self):
        self.logger.conn.close()

    def test_legacy_schema_is_nullable_and_has_no_new_identity_columns(self):
        columns = {
            row[1]: {"type": row[2], "notnull": row[3], "default": row[4]}
            for row in self.logger.conn.execute("PRAGMA table_info(trades)")
        }

        self.assertEqual(columns["id"]["type"], "INTEGER")
        self.assertEqual(columns["id"]["notnull"], 0)
        self.assertEqual(columns["timestamp"]["type"], "TEXT")
        self.assertEqual(columns["confidence"]["type"], "REAL")
        self.assertEqual(columns["ticket"]["type"], "INTEGER")
        self.assertEqual(columns["account"]["type"], "TEXT")
        self.assertTrue(all(item["notnull"] == 0 for item in columns.values()))
        self.assertTrue(all(item["default"] is None for item in columns.values()))
        self.assertNotIn("account_name", columns)
        self.assertNotIn("account_id", columns)
        self.assertNotIn("mt5_position_id", columns)
        self.assertNotIn("strategy_version", columns)
        self.assertNotIn("execution_contract_valid", columns)
        self.assertNotIn("planned_entry", columns)
        self.assertNotIn("actual_entry", columns)

    def test_entry_returns_database_record_id_distinct_from_broker_ticket(self):
        record_id = self.logger.log_trade_entry(
            _signal(), volume=0.01, ticket=7001, regime="stable", account="Live_Micro"
        )

        row = self.logger.conn.execute(
            "SELECT id, ticket, account, timestamp FROM trades WHERE id=?", (record_id,)
        ).fetchone()
        self.assertEqual(row[0], record_id)
        self.assertEqual(row[1], 7001)
        self.assertEqual(row[2], "Live_Micro")
        self.assertIsInstance(row[3], str)
        self.assertFalse(self.logger.conn.in_transaction)

    def test_ticket_is_not_unique_and_exit_updates_duplicate_tickets_without_account_scope(self):
        first_id = self.logger.log_trade_entry(
            _signal(pair="EURUSD", entry=1.0000), ticket=7002, account="Live_Micro"
        )
        second_id = self.logger.log_trade_entry(
            _signal(pair="GBPUSD", entry=2.0000), ticket=7002, account="Demo2"
        )
        self.assertNotEqual(first_id, second_id)

        index_rows = self.logger.conn.execute("PRAGMA index_list(trades)").fetchall()
        ticket_index = next(row for row in index_rows if row[1] == "idx_ticket")
        self.assertEqual(ticket_index[2], 0)  # indexed, but not UNIQUE

        exit_time = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)
        self.logger.log_trade_exit(7002, 1.25, exit_time, 1.0, "closed")

        rows = self.logger.conn.execute(
            "SELECT id, account, exit_price, exit_time, pnl, pnl_percent, result "
            "FROM trades WHERE ticket=? ORDER BY id", (7002,)
        ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual([row[0] for row in rows], [first_id, second_id])
        self.assertEqual([row[1] for row in rows], ["Live_Micro", "Demo2"])
        self.assertEqual([row[2] for row in rows], [1.25, 1.25])
        self.assertEqual([row[4] for row in rows], [1.0, 1.0])
        # The SELECT/fetchone uses the first entry price (1.0), then the
        # UPDATE applies that computed value to every matching ticket row.
        self.assertEqual([row[5] for row in rows], [100.0, 100.0])
        self.assertEqual([row[6] for row in rows], ["WIN", "WIN"])

    def test_missing_ticket_exit_is_a_silent_noop(self):
        before = self.logger.conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        result = self.logger.log_trade_exit(
            999999, 1.2, datetime.now(timezone.utc), 1.0, "missing"
        )
        after = self.logger.conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        self.assertIsNone(result)
        self.assertEqual(before, after)

    def test_planned_values_are_legacy_entry_fields_and_actual_entry_is_not_logged(self):
        record_id = self.logger.log_trade_entry(_signal(entry=1.2345), ticket=7003)
        row = self.logger.conn.execute(
            "SELECT entry, stop_loss, take_profit, exit_price FROM trades WHERE id=?",
            (record_id,),
        ).fetchone()
        self.assertEqual(row[:3], (1.2345, 1.2325, 1.2385))
        self.assertIsNone(row[3])

    def test_each_successful_write_is_committed_and_query_errors_propagate(self):
        self.logger.log_trade_entry(_signal(), ticket=7004)
        self.assertFalse(self.logger.conn.in_transaction)
        self.logger.log_trade_exit(
            7004, 1.101, datetime.now(timezone.utc), 1.0, "closed"
        )
        self.assertFalse(self.logger.conn.in_transaction)

        self.logger.conn.close()
        with self.assertRaises(sqlite3.ProgrammingError):
            self.logger.get_recent_pnls()

    def test_exit_database_errors_are_caught_and_reported_by_legacy_warning_path(self):
        self.logger.conn.close()
        with patch("builtins.print") as print_mock:
            result = self.logger.log_trade_exit(
                7005, 1.2, datetime.now(timezone.utc), 1.0, "closed"
            )
        self.assertIsNone(result)
        print_mock.assert_called_once()

    def test_partial_schema_migration_does_not_reconstruct_missing_base_columns(self):
        raw = sqlite3.connect(":memory:")
        raw.execute("CREATE TABLE trades (id INTEGER PRIMARY KEY, timestamp TEXT, pair TEXT)")
        raw.commit()

        with patch.object(legacy_trade_logger.sqlite3, "connect", return_value=raw):
            logger = TradeLogger(db_path="isolated-partial-schema")
            columns = {
                row[1] for row in logger.conn.execute("PRAGMA table_info(trades)")
            }

        self.assertIn("ticket", columns)
        self.assertIn("account", columns)
        self.assertNotIn("confidence", columns)
        logger.conn.close()
        raw.close()


if __name__ == "__main__":
    unittest.main()
