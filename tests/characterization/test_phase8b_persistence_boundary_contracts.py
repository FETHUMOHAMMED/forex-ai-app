"""Phase 8B contract-design characterization.

No production contract is implemented here. These tests assert the design
artifacts and the legacy identity semantics using only an in-memory database.
"""

from pathlib import Path
import sqlite3
import sys
import types
import unittest
from datetime import datetime, timezone


# The legacy logger imports pandas at module import time. Keep this test
# runnable in the repository's dependency-light environment without changing
# production code. The Phase 8B cases do not call pandas-backed analytics.
try:
    import pandas  # noqa: F401
except ModuleNotFoundError:
    sys.modules["pandas"] = types.SimpleNamespace()

import risk.trade_logger as legacy_trade_logger
from risk.trade_logger import TradeLogger


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "characterization" / "phase8b_persistence_boundary_contracts.md"
PHASE7_CONTRACT = ROOT / "packages" / "compatibility" / "canonical_trade_logger_contract.py"


def _signal(pair="EURUSD", entry=1.1000):
    return {
        "pair": pair,
        "signal": "BUY",
        "confidence": 0.83,
        "entry": entry,
        "stop_loss": entry - 0.0020,
        "take_profit": entry + 0.0040,
    }


class Phase8BContractDesignCharacterization(unittest.TestCase):
    def setUp(self):
        self.logger = TradeLogger(db_path=":memory:")

    def tearDown(self):
        self.logger.conn.close()

    def test_phase7_contract_remains_the_exact_eight_method_compatibility_surface(self):
        source = PHASE7_CONTRACT.read_text(encoding="utf-8")
        methods = (
            "log_trade_entry",
            "log_trade_exit",
            "get_recent_pnls",
            "get_recent_trade_stats",
            "get_regime_performance",
            "get_pair_performance",
            "get_daily_stats",
            "get_performance_stats",
        )
        for method in methods:
            self.assertIn(f"def {method}", source)
        self.assertNotIn("class CanonicalTradePersistenceContract", source)
        self.assertNotIn("class CanonicalExecutionIdentityContract", source)
        self.assertNotIn("class CanonicalTradeReadProjectionContract", source)

    def test_design_document_defines_separate_boundaries_without_schema_implementation(self):
        document = DOC.read_text(encoding="utf-8")
        for heading in (
            "### A. `CanonicalTradeLoggerContract`",
            "### B. `CanonicalTradePersistenceContract`",
            "### C. `CanonicalExecutionIdentityContract`",
            "### D. `CanonicalTradeReadProjectionContract`",
            "### E. Schema/migration lifecycle",
        ):
            self.assertIn(heading, document)
        self.assertIn("not implemented", document)
        self.assertIn("must never be conflated", document)
        self.assertIn("No generic `execute(sql)` repository interface", document)
        self.assertIn("broker-identifier field", document)
        self.assertIn("order ticket or a position", document)
        self.assertIn("packages/execution/mt5_identity.py", document)
        self.assertIn("find_record_ids_by_legacy_ticket", document)
        self.assertNotIn("find_record_ids_by_broker_ticket", document)
        self.assertIn("qualification/evidence projection", document)
        self.assertIn("cursor.description", document)
        self.assertIn("no defined lifecycle or concurrency contract", document)
        for newer_field in (
            "actual_entry_price",
            "actual_exit_price",
            "actual_volume",
            "commission",
            "swap",
        ):
            self.assertIn(newer_field, document)

    def test_database_record_id_and_broker_ticket_are_distinct(self):
        record_id = self.logger.log_trade_entry(
            _signal(), volume=0.01, ticket=8101, account="Live_Micro"
        )
        row = self.logger.conn.execute(
            "SELECT id, ticket FROM trades WHERE id=?", (record_id,)
        ).fetchone()
        self.assertEqual(row[0], record_id)
        self.assertEqual(row[1], 8101)
        self.assertNotEqual(record_id, 8101)

    def test_identity_projection_must_allow_duplicate_legacy_tickets(self):
        first = self.logger.log_trade_entry(
            _signal("EURUSD", 1.0), ticket=8102, account="Live_Micro"
        )
        second = self.logger.log_trade_entry(
            _signal("GBPUSD", 2.0), ticket=8102, account="Demo2"
        )
        ids = [
            row[0]
            for row in self.logger.conn.execute(
                "SELECT id FROM trades WHERE ticket=? ORDER BY id", (8102,)
            )
        ]
        self.assertEqual(ids, [first, second])

    def test_legacy_exit_semantics_remain_ticket_based_and_unscoped(self):
        self.logger.log_trade_entry(_signal("EURUSD", 1.0), ticket=8103, account="A")
        self.logger.log_trade_entry(_signal("GBPUSD", 2.0), ticket=8103, account="B")
        self.logger.log_trade_exit(
            8103,
            1.25,
            datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc),
            1.0,
            "closed",
        )
        rows = self.logger.conn.execute(
            "SELECT account, exit_price, pnl FROM trades WHERE ticket=? ORDER BY id",
            (8103,),
        ).fetchall()
        self.assertEqual(rows, [("A", 1.25, 1.0), ("B", 1.25, 1.0)])

    def test_legacy_schema_does_not_supply_new_execution_identity_or_actual_fields(self):
        columns = {
            row[1] for row in self.logger.conn.execute("PRAGMA table_info(trades)")
        }
        for absent in (
            "account_name",
            "account_id",
            "environment",
            "mt5_position_id",
            "mt5_deal_ticket",
            "planned_entry",
            "actual_entry",
            "actual_sl",
            "actual_tp",
            "execution_contract_valid",
        ):
            self.assertNotIn(absent, columns)

    def test_successful_writes_commit_and_query_errors_remain_observable(self):
        self.logger.log_trade_entry(_signal(), ticket=8104)
        self.assertFalse(self.logger.conn.in_transaction)
        self.logger.log_trade_exit(
            8104, 1.101, datetime.now(timezone.utc), 1.0, "closed"
        )
        self.assertFalse(self.logger.conn.in_transaction)
        self.logger.conn.close()
        with self.assertRaises(sqlite3.ProgrammingError):
            self.logger.get_recent_pnls()


if __name__ == "__main__":
    unittest.main()
