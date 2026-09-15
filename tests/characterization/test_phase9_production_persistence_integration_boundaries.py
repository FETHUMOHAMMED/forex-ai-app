"""Read-only Phase 9 production-persistence boundary characterization.

These tests inspect source and design artifacts only. The sole SQLite activity
uses an isolated in-memory database. No production module is imported or run.
"""

from __future__ import annotations

import ast
import hashlib
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "characterization" / "phase9_production_persistence_integration_audit.md"
TEST_SOURCE = Path(__file__).read_text(encoding="utf-8")
CONTRACT_SOURCE = (
    ROOT / "packages" / "compatibility" / "canonical_trade_logger_contract.py"
).read_text(encoding="utf-8")
ADAPTER_SOURCE = (
    ROOT / "packages" / "compatibility" / "canonical_trade_persistence_shadow.py"
).read_text(encoding="utf-8")
SHADOW_SOURCE = (
    ROOT / "packages" / "compatibility" / "legacy_trade_logger_shadow.py"
).read_text(encoding="utf-8")
IDENTITY_SOURCE = (ROOT / "packages" / "execution" / "mt5_identity.py").read_text(
    encoding="utf-8"
)
AUTO_TRADER_SOURCE = (ROOT / "ai-service" / "auto_trader_exness.py").read_text(
    encoding="utf-8"
)
LOGGER_SOURCE = (ROOT / "risk" / "trade_logger.py").read_text(encoding="utf-8")

BASELINE_SHA256 = (
    "1A33D16E8CCF6E9532448F23631AA5E34FE5E12864C9CF5A961ACFB525E959BF"
)


def _method_names_from_protocol() -> set[str]:
    tree = ast.parse(CONTRACT_SOURCE)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def _imports(source: str) -> list[ast.stmt]:
    return [node for node in ast.walk(ast.parse(source)) if isinstance(node, (ast.Import, ast.ImportFrom))]


class Phase9ProductionPersistenceBoundaryTests(unittest.TestCase):
    def test_phase7_contract_has_exactly_eight_methods(self):
        expected = {
            "log_trade_entry",
            "log_trade_exit",
            "get_recent_pnls",
            "get_recent_trade_stats",
            "get_regime_performance",
            "get_pair_performance",
            "get_daily_stats",
            "get_performance_stats",
        }
        self.assertEqual(_method_names_from_protocol(), expected)
        self.assertIn("class CanonicalTradeLoggerContract", CONTRACT_SOURCE)

    def test_phase7_method_signatures_remain_documented(self):
        expected_fragments = (
            "def log_trade_entry(",
            "def log_trade_exit(",
            "def get_recent_pnls(",
            "def get_recent_trade_stats(",
            "def get_regime_performance(",
            "def get_pair_performance(",
            "def get_daily_stats(",
            "def get_performance_stats(",
        )
        for fragment in expected_fragments:
            self.assertIn(fragment, CONTRACT_SOURCE)

    def test_phase8c_remains_explicitly_shadow_only_and_narrow(self):
        self.assertIn("class ShadowCanonicalTradePersistenceAdapter", ADAPTER_SOURCE)
        self.assertIn("shadow_only: bool = False", ADAPTER_SOURCE)
        self.assertIn("ShadowTradeLoggerAdapter", ADAPTER_SOURCE)
        self.assertNotIn("get_recent_pnls", ADAPTER_SOURCE)
        self.assertNotIn("execute(sql)", ADAPTER_SOURCE)
        self.assertIn(":memory:", SHADOW_SOURCE)

    def test_identity_terms_are_distinct_and_no_legacy_alias_is_defined(self):
        for term in (
            "TicketType.ORDER",
            "TicketType.POSITION",
            "TicketType.DEAL_ENTRY",
            "TicketType.DEAL_EXIT",
            "mt5_order_ticket",
            "mt5_position_ticket",
            "mt5_entry_deal_ticket",
            "mt5_exit_deal_ticket",
        ):
            self.assertIn(term, IDENTITY_SOURCE)

        for text in (ADAPTER_SOURCE,):
            self.assertNotIn("order_ticket = ticket", text)
            self.assertNotIn("position_ticket = ticket", text)
            self.assertNotIn("deal_ticket = ticket", text)

    def test_source_shows_current_full_logger_dependency_surface(self):
        live_methods = {
            "log_trade_entry",
            "log_trade_exit",
            "get_recent_pnls",
            "get_recent_trade_stats",
            "get_regime_performance",
            "get_pair_performance",
            "get_daily_stats",
        }
        for method in live_methods:
            self.assertIn(f"logger.{method}", AUTO_TRADER_SOURCE)
        self.assertIn("self.logger = logger", AUTO_TRADER_SOURCE)
        self.assertIn('TradeLogger(db_path="trades.db")', AUTO_TRADER_SOURCE)
        self.assertIn("def get_performance_stats", LOGGER_SOURCE)

    def test_legacy_connection_and_write_semantics_remain_observable(self):
        self.assertIn("sqlite3.connect(db_path, check_same_thread=False)", LOGGER_SOURCE)
        self.assertIn("self.conn =", LOGGER_SOURCE)
        self.assertIn("self.cursor =", LOGGER_SOURCE)
        self.assertIn("return self.cursor.lastrowid", LOGGER_SOURCE)
        self.assertIn("WHERE ticket=?", LOGGER_SOURCE)
        self.assertIn("self.conn.commit()", LOGGER_SOURCE)

    def test_phase9_artifacts_have_no_runtime_or_production_imports(self):
        forbidden_modules = {
            "MetaTrader5",
            "requests",
            "httpx",
            "urllib",
            "auto_trader_exness",
            "broker_exness",
            "real_ai_service",
            "ai_service_daemon",
        }
        for source in (TEST_SOURCE, ADAPTER_SOURCE):
            for node in _imports(source):
                if isinstance(node, ast.Import):
                    names = {alias.name.split(".")[0] for alias in node.names}
                else:
                    names = {node.module.split(".")[0]} if node.module else set()
                self.assertTrue(forbidden_modules.isdisjoint(names), names)

    def test_design_document_preserves_required_phase_boundaries(self):
        document = DOC.read_text(encoding="utf-8")
        for phrase in (
            "Phase 8C two-method adapter is a characterization boundary only",
            "trades.ticket",
            "SQLite trade record ID",
            "MT5 order ticket",
            "MT5 position ticket/identifier",
            "MT5 entry deal ticket",
            "MT5 exit deal ticket",
            "Option D target architecture",
            "Option B first eventual seam",
            "Directly replacing `TradeLogger` with the Phase 8C adapter is rejected",
            "No production integration is authorized",
        ):
            self.assertIn(phrase, document)

    def test_only_in_memory_sqlite_is_used_by_this_test(self):
        connection = sqlite3.connect(":memory:")
        try:
            connection.execute("CREATE TABLE identity_probe (id INTEGER PRIMARY KEY, ticket INTEGER)")
            connection.execute("INSERT INTO identity_probe(ticket) VALUES (?)", (7,))
            self.assertEqual(connection.execute("SELECT id, ticket FROM identity_probe").fetchone(), (1, 7))
        finally:
            connection.close()

        calls = [
            node
            for node in ast.walk(ast.parse(TEST_SOURCE))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "sqlite3"
            and node.func.attr == "connect"
        ]
        self.assertEqual(len(calls), 1)
        self.assertIsInstance(calls[0].args[0], ast.Constant)
        self.assertEqual(calls[0].args[0].value, ":memory:")

    def test_phase2_baseline_is_unchanged(self):
        baseline = ROOT / "tests" / "characterization" / "legacy_v3_baseline.json"
        digest = hashlib.sha256(baseline.read_bytes()).hexdigest().upper()
        self.assertEqual(digest, BASELINE_SHA256)


if __name__ == "__main__":
    unittest.main()
