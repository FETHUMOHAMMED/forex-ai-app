"""Phase 8C shadow persistence adapter characterization.

All database activity in these tests uses isolated SQLite ``:memory:``
connections.  No production caller, database, broker, MT5, network, cache,
or runtime configuration is imported or accessed.
"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# Keep this isolated test runnable without installing optional repository
# dependencies. The tested persistence paths do not call pandas or FastAPI.
try:
    import pandas  # noqa: F401
except ModuleNotFoundError:
    sys.modules["pandas"] = types.SimpleNamespace()

try:
    import fastapi  # noqa: F401
except ModuleNotFoundError:
    fastapi_module = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code=500, detail=None, headers=None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail
            self.headers = headers

    fastapi_module.HTTPException = HTTPException
    sys.modules["fastapi"] = fastapi_module

try:
    from starlette.responses import JSONResponse  # noqa: F401
except ModuleNotFoundError:
    responses_module = types.ModuleType("starlette.responses")
    responses_module.JSONResponse = type("JSONResponse", (), {})
    sys.modules["starlette.responses"] = responses_module

from packages.compatibility.canonical_trade_persistence_shadow import (  # noqa: E402
    ShadowCanonicalTradePersistenceAdapter,
    ShadowModeViolation,
)
from risk.trade_logger import TradeLogger  # noqa: E402


BASELINE_SHA256 = (
    "1A33D16E8CCF6E9532448F23631AA5E34FE5E12864C9CF5A961ACFB525E959BF"
)
ADAPTER_SOURCE = (
    ROOT / "packages" / "compatibility" / "canonical_trade_persistence_shadow.py"
)


def _signal(pair="EURUSD", entry=1.15123, direction="BUY"):
    return {
        "pair": pair,
        "signal": direction,
        "confidence": 0.83,
        "entry": entry,
        "stop_loss": entry - 0.00176,
        "take_profit": entry + 0.00431,
        "institutional_bias": "BREAKOUT",
        "institutional_score": 81.85,
        "dealer_pressure": "SELLING_PRESSURE",
        "liquidity_state": "SWEEP_SELL",
        "continuation_prob": 0.50,
    }


def _logger():
    logger = TradeLogger(db_path=":memory:")
    logger.shadow_only = True
    return logger


def _row(logger, ticket):
    return logger.conn.execute(
        "SELECT pair, signal, confidence, entry, stop_loss, take_profit, "
        "exit_price, exit_time, pnl, pnl_percent, result, volume, ticket, "
        "regime, reason, account FROM trades WHERE ticket=? ORDER BY id",
        (ticket,),
    ).fetchall()


class Phase8CShadowPersistenceAdapterTests(unittest.TestCase):
    def tearDown(self):
        for value in getattr(self, "_closeables", []):
            value.conn.close()

    def _track(self, *values):
        self._closeables = list(values)

    def test_adapter_is_explicitly_shadow_only_and_narrow(self):
        logger = _logger()
        self._track(logger)
        adapter = ShadowCanonicalTradePersistenceAdapter(logger, shadow_only=True)

        self.assertTrue(adapter.shadow_only)
        self.assertTrue(hasattr(adapter, "log_trade_entry"))
        self.assertTrue(hasattr(adapter, "log_trade_exit"))
        self.assertFalse(hasattr(adapter, "get_recent_pnls"))
        self.assertFalse(hasattr(adapter, "execute"))

    def test_entry_preserves_record_id_account_ticket_and_planned_fields(self):
        direct = _logger()
        wrapped_logger = _logger()
        self._track(direct, wrapped_logger)
        adapter = ShadowCanonicalTradePersistenceAdapter(
            wrapped_logger, shadow_only=True
        )
        signal = _signal()

        direct_id = direct.log_trade_entry(
            signal, volume=0.12, ticket=9101, regime="volatile", account="Live_Micro"
        )
        adapter_id = adapter.log_trade_entry(
            signal, volume=0.12, ticket=9101, regime="volatile", account="Live_Micro"
        )

        self.assertEqual(direct_id, adapter_id)
        self.assertEqual(direct_id, 1)
        self.assertEqual(_row(direct, 9101), _row(wrapped_logger, 9101))
        row = wrapped_logger.conn.execute(
            "SELECT id, entry, stop_loss, take_profit, ticket, account "
            "FROM trades WHERE id=?",
            (adapter_id,),
        ).fetchone()
        self.assertEqual(row, (1, signal["entry"], signal["stop_loss"], signal["take_profit"], 9101, "Live_Micro"))

    def test_exit_preserves_legacy_broad_ticket_update_and_commit(self):
        direct = _logger()
        wrapped_logger = _logger()
        self._track(direct, wrapped_logger)
        adapter = ShadowCanonicalTradePersistenceAdapter(
            wrapped_logger, shadow_only=True
        )
        exit_time = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)

        for logger, writer in ((direct, direct.log_trade_entry), (adapter, adapter.log_trade_entry)):
            writer(_signal("EURUSD", 1.0), ticket=9102, account="Live_Micro")
            writer(_signal("GBPUSD", 2.0), ticket=9102, account="Demo2")

        direct_result = direct.log_trade_exit(9102, 1.25, exit_time, 1.0, "closed")
        adapter_result = adapter.log_trade_exit(9102, 1.25, exit_time, 1.0, "closed")

        self.assertIsNone(direct_result)
        self.assertIsNone(adapter_result)
        self.assertEqual(_row(direct, 9102), _row(wrapped_logger, 9102))
        self.assertEqual(
            [row[-1] for row in _row(wrapped_logger, 9102)], ["Live_Micro", "Demo2"]
        )
        self.assertFalse(direct.conn.in_transaction)
        self.assertFalse(wrapped_logger.conn.in_transaction)

    def test_duplicate_ticket_remains_an_untyped_legacy_value(self):
        logger = _logger()
        self._track(logger)
        adapter = ShadowCanonicalTradePersistenceAdapter(logger, shadow_only=True)

        adapter.log_trade_entry(_signal(), ticket=9103, account="Live_Micro")
        adapter.log_trade_entry(_signal("GBPUSD"), ticket=9103, account="Demo2")

        rows = logger.conn.execute(
            "SELECT ticket, account FROM trades WHERE ticket=? ORDER BY id", (9103,)
        ).fetchall()
        self.assertEqual(rows, [(9103, "Live_Micro"), (9103, "Demo2")])
        self.assertFalse(hasattr(adapter, "order_ticket"))
        self.assertFalse(hasattr(adapter, "position_ticket"))
        self.assertFalse(hasattr(adapter, "deal_ticket"))

    def test_missing_ticket_is_the_legacy_silent_noop(self):
        direct = _logger()
        wrapped_logger = _logger()
        self._track(direct, wrapped_logger)
        adapter = ShadowCanonicalTradePersistenceAdapter(
            wrapped_logger, shadow_only=True
        )
        signal = _signal()
        direct.log_trade_entry(signal, ticket=9104)
        adapter.log_trade_entry(signal, ticket=9104)

        self.assertIsNone(
            direct.log_trade_exit(9199, 1.15, datetime.now(timezone.utc), 2.5, "missing")
        )
        self.assertIsNone(
            adapter.log_trade_exit(9199, 1.15, datetime.now(timezone.utc), 2.5, "missing")
        )
        self.assertEqual(_row(direct, 9104), _row(wrapped_logger, 9104))

    def test_entry_errors_propagate_and_exit_errors_keep_legacy_catching(self):
        logger = _logger()
        self._track(logger)
        adapter = ShadowCanonicalTradePersistenceAdapter(logger, shadow_only=True)
        logger.conn.close()

        with self.assertRaises(sqlite3.ProgrammingError):
            adapter.log_trade_entry(_signal(), ticket=9105)

        with patch("builtins.print") as print_mock:
            self.assertIsNone(
                adapter.log_trade_exit(
                    9105, 1.15, datetime.now(timezone.utc), 2.5, "closed"
                )
            )
        print_mock.assert_called_once()

    def test_planned_values_are_not_reinterpreted_as_actual_execution_values(self):
        logger = _logger()
        self._track(logger)
        adapter = ShadowCanonicalTradePersistenceAdapter(logger, shadow_only=True)
        signal = _signal(entry=1.2345)
        record_id = adapter.log_trade_entry(signal, ticket=9106)

        columns = {
            row[1] for row in logger.conn.execute("PRAGMA table_info(trades)")
        }
        row = logger.conn.execute(
            "SELECT entry, stop_loss, take_profit, exit_price FROM trades WHERE id=?",
            (record_id,),
        ).fetchone()
        self.assertEqual(row[:3], (signal["entry"], signal["stop_loss"], signal["take_profit"]))
        self.assertIsNone(row[3])
        self.assertNotIn("actual_entry", columns)
        self.assertNotIn("actual_sl", columns)
        self.assertNotIn("actual_tp", columns)

    def test_shadow_only_and_memory_guards_reject_unsafe_dependencies(self):
        logger = _logger()
        self._track(logger)

        with self.assertRaises(ShadowModeViolation):
            ShadowCanonicalTradePersistenceAdapter(logger)

        with self.assertRaises(ShadowModeViolation):
            ShadowCanonicalTradePersistenceAdapter(
                SimpleNamespace(conn=sqlite3.connect(":memory:")), shadow_only=True
            )

        file_like = SimpleNamespace(
            shadow_only=True,
            conn=SimpleNamespace(
                execute=lambda _sql: SimpleNamespace(
                    fetchall=lambda: [(0, "main", "file-backed.sqlite")]
                )
            ),
        )
        with self.assertRaises(ShadowModeViolation):
            ShadowCanonicalTradePersistenceAdapter(file_like, shadow_only=True)

    def test_adapter_has_no_unsafe_production_dependencies(self):
        source = ADAPTER_SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "MetaTrader5",
            "auto_trader_exness",
            "trades.db",
            "signals_cache",
            "runtime_config",
            "requests",
            "httpx",
            "urllib",
            "mt5_identity",
            "execute(sql)",
        ):
            self.assertNotIn(forbidden, source)

        baseline = ROOT / "tests" / "characterization" / "legacy_v3_baseline.json"
        self.assertEqual(hashlib.sha256(baseline.read_bytes()).hexdigest().upper(), BASELINE_SHA256)


if __name__ == "__main__":
    unittest.main()
