"""Phase 10 legacy-vs-façade characterization.

All actual persistence tests use independent SQLite ``:memory:`` loggers.
The façade is never imported by a production caller, and no MT5, broker,
network, cache, configuration, or file-backed database is used.
"""

from __future__ import annotations

import ast
import hashlib
import sqlite3
import sys
import types
import unittest
from datetime import datetime, timezone
from inspect import signature
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
FACADE_SOURCE_PATH = ROOT / "packages" / "compatibility" / "canonical_trade_logger_facade.py"
FACADE_SOURCE = FACADE_SOURCE_PATH.read_text(encoding="utf-8")
AUTO_TRADER_SOURCE = (ROOT / "ai-service" / "auto_trader_exness.py").read_text(encoding="utf-8")
BASELINE_SHA256 = (
    "1A33D16E8CCF6E9532448F23631AA5E34FE5E12864C9CF5A961ACFB525E959BF"
)


# The legacy logger imports pandas for one query. If pandas is unavailable,
# provide only the DataFrame operations exercised by this isolated test.
try:
    import pandas  # noqa: F401
except ModuleNotFoundError:
    class _Series:
        def __init__(self, values):
            self.values = values

        def __eq__(self, other):
            return [value == other for value in self.values]

        def sum(self):
            return sum(value for value in self.values if value is not None)

        def mean(self):
            values = [value for value in self.values if value is not None]
            return sum(values) / len(values) if values else float("nan")

        def max(self):
            return max(value for value in self.values if value is not None)

        def min(self):
            return min(value for value in self.values if value is not None)

    class _DataFrame:
        def __init__(self, rows, columns):
            self.rows = rows
            self.columns = columns

        @property
        def empty(self):
            return not self.rows

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, key):
            if isinstance(key, str):
                index = self.columns.index(key)
                return _Series([row[index] for row in self.rows])
            if isinstance(key, list) and all(isinstance(value, bool) for value in key):
                return _DataFrame(
                    [row for row, keep in zip(self.rows, key) if keep], self.columns
                )
            raise TypeError(key)

    def _read_sql_query(sql, conn):
        cursor = conn.execute(sql)
        return _DataFrame(
            cursor.fetchall(), [description[0] for description in cursor.description]
        )

    pandas_stub = types.ModuleType("pandas")
    pandas_stub.read_sql_query = _read_sql_query
    sys.modules["pandas"] = pandas_stub


# Importing the compatibility package imports the existing shadow module. Its
# optional web dependencies are stubbed only when absent; no web code runs.
try:
    import fastapi  # noqa: F401
except ModuleNotFoundError:
    fastapi_stub = types.ModuleType("fastapi")
    fastapi_stub.HTTPException = type("HTTPException", (Exception,), {})
    sys.modules["fastapi"] = fastapi_stub

try:
    from starlette.responses import JSONResponse  # noqa: F401
except ModuleNotFoundError:
    starlette_stub = types.ModuleType("starlette")
    responses_stub = types.ModuleType("starlette.responses")
    responses_stub.JSONResponse = type("JSONResponse", (), {})
    starlette_stub.responses = responses_stub
    sys.modules["starlette"] = starlette_stub
    sys.modules["starlette.responses"] = responses_stub

from packages.compatibility.canonical_trade_logger_contract import (  # noqa: E402
    CanonicalTradeLoggerContract,
)
from packages.compatibility.canonical_trade_logger_facade import (  # noqa: E402
    CanonicalTradeLoggerFacade,
)
from risk.trade_logger import TradeLogger  # noqa: E402


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
        "dealer_pressure": "SELLING_PRESSURE",
        "liquidity_state": "SWEEP_SELL",
        "continuation_prob": 0.50,
    }


def _logger():
    return TradeLogger(db_path=":memory:")


def _rows(logger, ticket):
    return logger.conn.execute(
        "SELECT id, pair, signal, confidence, entry, stop_loss, take_profit, "
        "exit_price, exit_time, pnl, pnl_percent, result, volume, ticket, "
        "regime, reason, account FROM trades WHERE ticket=? ORDER BY id",
        (ticket,),
    ).fetchall()


def _seed(logger):
    logger.log_trade_entry(
        _signal("EURUSD", 1.0), volume=0.10, ticket=5001, regime="trending", account="A"
    )
    logger.log_trade_exit(
        5001, 1.1, datetime.now(timezone.utc), 2.0, "win"
    )
    logger.log_trade_entry(
        _signal("GBPUSD", 2.0), volume=0.20, ticket=5002, regime="ranging", account="B"
    )
    logger.log_trade_exit(
        5002, 2.1, datetime.now(timezone.utc), -1.0, "loss"
    )
    logger.log_trade_entry(
        _signal("EURUSD", 1.5), volume=0.15, ticket=5003, regime="trending", account="A"
    )
    logger.log_trade_exit(
        5003, 1.5, datetime.now(timezone.utc), 0.0, "flat"
    )
    logger.log_trade_entry(
        _signal("USDJPY", 150.0), volume=0.05, ticket=5004, regime="open", account="A"
    )


class Phase10EightMethodFacadeTests(unittest.TestCase):
    def setUp(self):
        self.direct = _logger()
        self.wrapped_logger = _logger()
        self.facade = CanonicalTradeLoggerFacade(self.wrapped_logger)

    def tearDown(self):
        for logger in (self.direct, self.wrapped_logger):
            try:
                logger.conn.close()
            except sqlite3.ProgrammingError:
                pass

    def test_facade_satisfies_unchanged_eight_method_contract(self):
        self.assertIsInstance(self.facade, CanonicalTradeLoggerContract)
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
        self.assertEqual(
            {name for name in methods if hasattr(self.facade, name)}, set(methods)
        )
        for name in methods:
            contract_parameters = list(signature(getattr(CanonicalTradeLoggerContract, name)).parameters.values())[1:]
            facade_parameters = list(signature(getattr(self.facade, name)).parameters.values())
            self.assertEqual(facade_parameters, contract_parameters)

    def test_entry_legacy_and_facade_match_for_nullable_duplicate_and_account_values(self):
        inputs = [
            (_signal(), {"volume": 0.10, "ticket": None, "regime": None, "account": None}),
            (_signal("GBPUSD", 2.0), {"volume": None, "ticket": 6001, "regime": "ranging", "account": "Live_Micro"}),
            (_signal("EURUSD", 3.0), {"volume": 0.20, "ticket": 6001, "regime": "volatile", "account": "Demo2"}),
        ]
        direct_ids = [self.direct.log_trade_entry(signal, **kwargs) for signal, kwargs in inputs]
        facade_ids = [self.facade.log_trade_entry(signal, **kwargs) for signal, kwargs in inputs]

        self.assertEqual(direct_ids, facade_ids)
        self.assertEqual(direct_ids, [1, 2, 3])
        self.assertEqual(_rows(self.direct, 6001), _rows(self.wrapped_logger, 6001))
        self.assertEqual(
            self.direct.conn.execute(
                "SELECT ticket, account FROM trades WHERE id=?", (1,)
            ).fetchone(),
            (None, None),
        )
        timestamp = self.direct.conn.execute(
            "SELECT timestamp FROM trades WHERE id=1"
        ).fetchone()[0]
        self.assertIsInstance(datetime.fromisoformat(timestamp), datetime)

    def test_exit_legacy_and_facade_match_for_duplicate_and_missing_tickets(self):
        for logger, writer in (
            (self.direct, self.direct.log_trade_entry),
            (self.facade, self.facade.log_trade_entry),
        ):
            writer(_signal("EURUSD", 1.0), ticket=6002, account="A")
            writer(_signal("GBPUSD", 2.0), ticket=6002, account="B")

        exit_time = datetime(2026, 8, 22, 10, 0, tzinfo=timezone.utc)
        self.assertIsNone(self.direct.log_trade_exit(6002, 1.25, exit_time, 1.0, "closed"))
        self.assertIsNone(self.facade.log_trade_exit(6002, 1.25, exit_time, 1.0, "closed"))
        self.assertEqual(_rows(self.direct, 6002), _rows(self.wrapped_logger, 6002))
        self.assertEqual(
            [row[-1] for row in _rows(self.wrapped_logger, 6002)], ["A", "B"]
        )
        self.assertFalse(self.direct.conn.in_transaction)
        self.assertFalse(self.wrapped_logger.conn.in_transaction)

        before = _rows(self.wrapped_logger, 6002)
        self.assertIsNone(self.facade.log_trade_exit(6999, 1.25, exit_time, 1.0, "missing"))
        self.assertEqual(before, _rows(self.wrapped_logger, 6002))

    def test_query_methods_match_independently_seeded_legacy_behavior(self):
        _seed(self.direct)
        _seed(self.wrapped_logger)

        self.assertEqual(self.direct.get_recent_pnls(100), self.facade.get_recent_pnls(100))
        self.assertEqual(
            self.direct.get_recent_trade_stats(days=30, account="A"),
            self.facade.get_recent_trade_stats(days=30, account="A"),
        )
        self.assertEqual(
            self.direct.get_recent_trade_stats(days=30),
            self.facade.get_recent_trade_stats(days=30),
        )
        self.assertEqual(
            self.direct.get_regime_performance(days=30),
            self.facade.get_regime_performance(days=30),
        )
        self.assertEqual(
            self.direct.get_pair_performance(days=30),
            self.facade.get_pair_performance(days=30),
        )
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(
            self.direct.get_daily_stats(today), self.facade.get_daily_stats(today)
        )
        self.assertEqual(
            self.direct.get_performance_stats(), self.facade.get_performance_stats()
        )

    def test_empty_and_null_query_behavior_matches(self):
        self.assertEqual(self.direct.get_recent_pnls(), self.facade.get_recent_pnls())
        self.assertEqual(
            self.direct.get_recent_trade_stats(), self.facade.get_recent_trade_stats()
        )
        self.assertEqual(
            self.direct.get_regime_performance(), self.facade.get_regime_performance()
        )
        self.assertEqual(
            self.direct.get_pair_performance(), self.facade.get_pair_performance()
        )
        self.assertIsNone(self.direct.get_daily_stats("1900-01-01"))
        self.assertIsNone(self.facade.get_daily_stats("1900-01-01"))
        self.assertEqual(
            self.direct.get_performance_stats(), self.facade.get_performance_stats()
        )

    def test_query_errors_propagate_identically(self):
        self.direct.conn.close()
        self.wrapped_logger.conn.close()
        query_calls = (
            lambda logger: logger.get_recent_pnls(),
            lambda logger: logger.get_recent_trade_stats(),
            lambda logger: logger.get_regime_performance(),
            lambda logger: logger.get_pair_performance(),
            lambda logger: logger.get_daily_stats("2026-08-22"),
            lambda logger: logger.get_performance_stats(),
        )
        for call in query_calls:
            with self.assertRaises(sqlite3.ProgrammingError):
                call(self.direct)
            with self.assertRaises(sqlite3.ProgrammingError):
                call(self.facade)

    def test_entry_and_exit_error_behavior_is_not_translated(self):
        self.direct.conn.close()
        self.wrapped_logger.conn.close()
        with self.assertRaises(sqlite3.ProgrammingError):
            self.direct.log_trade_entry(_signal(), ticket=6003)
        with self.assertRaises(sqlite3.ProgrammingError):
            self.facade.log_trade_entry(_signal(), ticket=6003)

        with patch("builtins.print") as direct_print:
            self.assertIsNone(
                self.direct.log_trade_exit(
                    6003, 1.1, datetime.now(timezone.utc), 1.0, "closed"
                )
            )
        with patch("builtins.print") as facade_print:
            self.assertIsNone(
                self.facade.log_trade_exit(
                    6003, 1.1, datetime.now(timezone.utc), 1.0, "closed"
                )
            )
        direct_print.assert_called_once()
        facade_print.assert_called_once()

    def test_lifecycle_is_delegated_not_redefined(self):
        self.assertTrue(hasattr(self.wrapped_logger, "conn"))
        self.assertTrue(hasattr(self.wrapped_logger, "cursor"))
        self.assertFalse(hasattr(self.facade, "conn"))
        self.assertFalse(hasattr(self.facade, "cursor"))
        self.assertIn("check_same_thread=False", (ROOT / "risk" / "trade_logger.py").read_text(encoding="utf-8"))
        self.assertNotIn("def close", FACADE_SOURCE)

    def test_facade_has_no_sql_identity_or_production_wiring(self):
        tree = ast.parse(FACADE_SOURCE)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        self.assertNotIn("sqlite3", imported)
        self.assertNotIn("MetaTrader5", imported)
        self.assertNotIn("requests", imported)
        for forbidden in (
            "sqlite3",
            "SELECT ",
            "CREATE TABLE",
            "MetaTrader5",
            "broker_exness",
            "auto_trader_exness",
            "trades.db",
            "mt5_identity",
            "order_ticket",
            "position_ticket",
            "deal_ticket",
        ):
            self.assertNotIn(forbidden, FACADE_SOURCE)
        self.assertNotIn("CanonicalTradeLoggerFacade", AUTO_TRADER_SOURCE)

    def test_phase2_baseline_is_unchanged(self):
        baseline = ROOT / "tests" / "characterization" / "legacy_v3_baseline.json"
        self.assertEqual(
            hashlib.sha256(baseline.read_bytes()).hexdigest().upper(), BASELINE_SHA256
        )


if __name__ == "__main__":
    unittest.main()
