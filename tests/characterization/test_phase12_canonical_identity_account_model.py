"""Pure Phase 12 identity/account model characterization.

No production persistence, MT5, broker, network, cache, configuration, or
file-backed database is used.
"""

from __future__ import annotations

import ast
import hashlib
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from packages.execution.canonical_execution_identity import (
    AccountScope,
    DealExecution,
    DealIdentity,
    DealRole,
    ExecutionLineage,
    LegacyTicketValue,
    OrderIdentity,
    PositionIdentity,
    TradeRecordId,
)


ROOT = Path(__file__).resolve().parents[2]
MODEL_SOURCE_PATH = ROOT / "packages" / "execution" / "canonical_execution_identity.py"
MODEL_SOURCE = MODEL_SOURCE_PATH.read_text(encoding="utf-8")
DOC_SOURCE = (
    ROOT / "docs" / "characterization" / "phase12_canonical_identity_account_model.md"
).read_text(encoding="utf-8")
BASELINE_SHA256 = (
    "1A33D16E8CCF6E9532448F23631AA5E34FE5E12864C9CF5A961ACFB525E959BF"
)


class Phase12CanonicalIdentityTests(unittest.TestCase):
    def setUp(self):
        self.account_a = AccountScope(
            broker="Exness",
            login=1001,
            server="ServerA",
            environment="DEMO",
            local_account_id="A",
        )
        self.account_b = AccountScope(
            broker="Exness",
            login=2002,
            server="ServerB",
            environment="LIVE",
            local_account_id="B",
        )

    def test_account_scope_is_explicit_and_exactly_scoped(self):
        same = AccountScope("Exness", 1001, "ServerA", "DEMO", "A")
        self.assertEqual(self.account_a, same)
        self.assertNotEqual(self.account_a, self.account_b)
        self.assertEqual(self.account_a.login, 1001)
        self.assertEqual(self.account_a.server, "ServerA")
        self.assertEqual(self.account_a.environment, "DEMO")

    def test_invalid_and_missing_account_identity_is_rejected(self):
        invalid_cases = (
            ("", 1001, "ServerA", "DEMO"),
            ("Exness", 0, "ServerA", "DEMO"),
            ("Exness", 1001, "", "DEMO"),
            ("Exness", 1001, "ServerA", ""),
        )
        for args in invalid_cases:
            with self.assertRaises(ValueError):
                AccountScope(*args)

    def test_order_position_deal_and_record_id_are_distinct_types(self):
        order_a = OrderIdentity(self.account_a, 123)
        position_a = PositionIdentity(self.account_a, 123)
        deal_a = DealIdentity(self.account_a, 123, DealRole.ENTRY)
        order_b = OrderIdentity(self.account_b, 123)
        record = TradeRecordId(123)

        self.assertNotEqual(order_a, position_a)
        self.assertNotEqual(order_a, deal_a)
        self.assertNotEqual(position_a, deal_a)
        self.assertNotEqual(order_a, order_b)
        self.assertNotEqual(order_a, record)
        self.assertEqual(order_a.ticket_id, position_a.ticket_id)

    def test_legacy_ticket_is_opaque_and_has_no_typed_conversion(self):
        legacy = LegacyTicketValue(123)
        self.assertEqual(legacy.value, 123)
        self.assertFalse(hasattr(legacy, "order"))
        self.assertFalse(hasattr(legacy, "position"))
        self.assertFalse(hasattr(legacy, "deal"))
        self.assertNotEqual(legacy, OrderIdentity(self.account_a, 123))

    def test_full_single_fill_entry_lineage(self):
        position = PositionIdentity(self.account_a, 123)
        entry = DealExecution(
            DealIdentity(self.account_a, 301, DealRole.ENTRY, position),
            quantity=0.10,
            price=1.1000,
            execution_time=datetime.now(timezone.utc),
            source_event_id="entry-301",
        )
        lineage = ExecutionLineage(
            account=self.account_a,
            local_trade_record_id=TradeRecordId(7),
            order=OrderIdentity(self.account_a, 201),
            position=position,
            entry_deals=(entry,),
        )
        self.assertEqual(lineage.order.ticket_id, 201)
        self.assertEqual(lineage.position.ticket_id, 123)
        self.assertEqual(lineage.entry_deals[0].quantity, 0.10)
        self.assertEqual(lineage.local_trade_record_id.value, 7)

    def test_multi_fill_entry_and_partial_close_lineage(self):
        position = PositionIdentity(self.account_a, 500)
        entries = tuple(
            DealExecution(
                DealIdentity(self.account_a, ticket, DealRole.ENTRY, position),
                quantity=quantity,
                price=1.1,
            )
            for ticket, quantity in ((501, 0.04), (502, 0.06))
        )
        exits = tuple(
            DealExecution(
                DealIdentity(self.account_a, ticket, DealRole.EXIT, position),
                quantity=quantity,
                price=1.2,
            )
            for ticket, quantity in ((601, 0.03), (602, 0.07))
        )
        lineage = ExecutionLineage(
            account=self.account_a,
            order=OrderIdentity(self.account_a, 400),
            position=position,
            entry_deals=entries,
            exit_deals=exits,
        )
        self.assertEqual([deal.quantity for deal in lineage.entry_deals], [0.04, 0.06])
        self.assertEqual([deal.quantity for deal in lineage.exit_deals], [0.03, 0.07])
        self.assertEqual(len(lineage.entry_deals), 2)
        self.assertEqual(len(lineage.exit_deals), 2)

    def test_duplicate_and_out_of_order_events_are_preserved_not_reconciled(self):
        position = PositionIdentity(self.account_a, 700)
        later = datetime(2026, 8, 22, 10, 5, tzinfo=timezone.utc)
        earlier = datetime(2026, 8, 22, 10, 1, tzinfo=timezone.utc)
        first = DealExecution(
            DealIdentity(self.account_a, 701, DealRole.EXIT, position),
            quantity=0.05,
            execution_time=later,
            source_event_id="event-701",
        )
        duplicate = DealExecution(
            DealIdentity(self.account_a, 701, DealRole.EXIT, position),
            quantity=0.05,
            execution_time=earlier,
            source_event_id="event-701",
        )
        lineage = ExecutionLineage(
            account=self.account_a,
            position=position,
            exit_deals=(first, duplicate),
        )
        self.assertEqual(len(lineage.exit_deals), 2)
        self.assertEqual(lineage.exit_deals[0].execution_time, later)
        self.assertEqual(lineage.exit_deals[1].execution_time, earlier)
        self.assertEqual(
            lineage.exit_deals[0].source_event_id,
            lineage.exit_deals[1].source_event_id,
        )

    def test_missing_order_position_local_record_and_event_fields_are_representable(self):
        deal = DealExecution(
            DealIdentity(self.account_a, 801, DealRole.ENTRY),
            quantity=None,
            price=None,
            execution_time=None,
            source_event_id=None,
        )
        lineage = ExecutionLineage(
            account=self.account_a,
            order=None,
            position=None,
            local_trade_record_id=None,
            entry_deals=(deal,),
        )
        self.assertIsNone(lineage.order)
        self.assertIsNone(lineage.position)
        self.assertIsNone(lineage.local_trade_record_id)
        self.assertIsNone(lineage.entry_deals[0].execution_time)

    def test_cross_account_lineage_and_cross_account_deal_reference_are_rejected(self):
        with self.assertRaises(ValueError):
            ExecutionLineage(
                account=self.account_a,
                order=OrderIdentity(self.account_b, 901),
            )

        foreign_position = PositionIdentity(self.account_b, 902)
        with self.assertRaises(ValueError):
            DealIdentity(self.account_a, 903, DealRole.EXIT, foreign_position)

    def test_wrong_deal_role_or_position_reference_is_rejected(self):
        position_a = PositionIdentity(self.account_a, 1000)
        wrong_role = DealExecution(
            DealIdentity(self.account_a, 1001, DealRole.EXIT, position_a)
        )
        with self.assertRaises(ValueError):
            ExecutionLineage(
                account=self.account_a,
                position=position_a,
                entry_deals=(wrong_role,),
            )

        other_position = PositionIdentity(self.account_a, 1002)
        mismatched = DealExecution(
            DealIdentity(self.account_a, 1003, DealRole.EXIT, other_position)
        )
        with self.assertRaises(ValueError):
            ExecutionLineage(
                account=self.account_a,
                position=position_a,
                exit_deals=(mismatched,),
            )

    def test_invalid_identity_values_are_rejected(self):
        with self.assertRaises(ValueError):
            OrderIdentity(self.account_a, 0)
        with self.assertRaises(ValueError):
            PositionIdentity(self.account_a, -1)
        with self.assertRaises(ValueError):
            DealIdentity(self.account_a, 0, DealRole.ENTRY)
        with self.assertRaises(ValueError):
            TradeRecordId(0)
        with self.assertRaises(ValueError):
            DealExecution(DealIdentity(self.account_a, 1101, DealRole.ENTRY), quantity=0)

    def test_value_objects_have_basic_serializable_structure(self):
        order = OrderIdentity(self.account_a, 1201)
        data = asdict(order)
        self.assertEqual(data["ticket_id"], 1201)
        self.assertEqual(data["account"]["login"], 1001)

    def test_static_safety_and_phase_artifact_integrity(self):
        tree = ast.parse(MODEL_SOURCE)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        for forbidden in (
            "MetaTrader5",
            "broker_exness",
            "auto_trader_exness",
            "sqlite3",
            "requests",
            "httpx",
            "urllib",
            "risk.trade_logger",
        ):
            self.assertNotIn(forbidden, imported)
        for forbidden_text in (
            "trades.db",
            "CREATE TABLE",
            "SELECT ",
            "INSERT ",
            "UPDATE ",
            "DELETE ",
            "MetaTrader5",
            "broker_exness",
            "auto_trader_exness",
        ):
            self.assertNotIn(forbidden_text, MODEL_SOURCE)
        self.assertIn("legacy ticket", DOC_SOURCE.lower())
        self.assertIn("partial", DOC_SOURCE.lower())
        self.assertIn("account scope", DOC_SOURCE.lower())

        baseline = ROOT / "tests" / "characterization" / "legacy_v3_baseline.json"
        self.assertEqual(
            hashlib.sha256(baseline.read_bytes()).hexdigest().upper(), BASELINE_SHA256
        )


if __name__ == "__main__":
    unittest.main()
