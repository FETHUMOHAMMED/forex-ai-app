"""Offline validation of the Phase 17 evidence template only."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / "docs" / "characterization" / "phase17_evidence_template.json"

REQUIRED_TOP_LEVEL = {
    "manifest",
    "account_snapshots",
    "requests",
    "broker_results",
    "position_snapshots_before",
    "position_snapshots_after",
    "history_orders",
    "history_deals",
    "retrieval_batches",
    "case_matrix",
    "collision_analysis",
    "activation_evidence",
}

CASE_IDS = {
    "CASE_01_ONE_ORDER_ONE_DEAL_ONE_POSITION",
    "CASE_02_ONE_ORDER_MULTIPLE_ENTRY_DEALS",
    "CASE_03_PARTIAL_FILL",
    "CASE_04_PARTIAL_CLOSE",
    "CASE_05_FULL_CLOSE",
    "CASE_06_CLOSE_REOPEN",
    "CASE_07_MULTIPLE_SAME_SYMBOL_POSITIONS",
    "CASE_08_TWO_ACCOUNT_SERVER_SCOPES",
    "CASE_09_REPEATED_HISTORY_RETRIEVAL",
    "CASE_10_DUPLICATE_REPLAYED_EVENT",
}

CASE_STATUSES = {"CAPTURED", "NOT_OBSERVED", "UNAVAILABLE"}
PLACEHOLDER_RE = re.compile(r"^SANITIZED_|^TEMPLATE_|^1970-01-01T")
SECRET_MARKERS = (
    "password",
    "api_key",
    "access_token",
    "private key",
    "-----begin",
    "mt5_password",
    "forex_api_key",
)
ALLOWED_SECRET_METADATA_KEYS = {
    "credential_secret_removal_confirmed",
}


def walk_strings(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key), child
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)


class Phase17EvidenceTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with TEMPLATE_PATH.open("r", encoding="utf-8") as handle:
            cls.template = json.load(handle)

    def test_required_top_level_sections_exist(self):
        self.assertEqual(set(self.template), REQUIRED_TOP_LEVEL)

    def test_manifest_contract(self):
        manifest = self.template["manifest"]
        required = {
            "capture_id",
            "source_class",
            "collector_tool_version",
            "source_system",
            "broker",
            "account_scope",
            "server_scope",
            "environment",
            "capture_start_utc",
            "capture_end_utc",
            "retrieval_windows",
            "pagination_information",
            "completeness_declaration",
            "sanitization_method",
            "credential_secret_removal_confirmed",
            "historical_export_vs_recorded_response_vs_synthetic_replay",
            "immutable_after_collection",
            "provenance_reference",
            "reviewer_status",
        }
        self.assertTrue(required.issubset(manifest))
        self.assertTrue(manifest["credential_secret_removal_confirmed"])
        self.assertEqual(manifest["source_class"], "TEMPLATE_ONLY_NOT_EVIDENCE")

    def test_account_scope_fields(self):
        required = {
            "broker",
            "login_account_alias",
            "server",
            "environment",
            "margin_account_mode",
            "currency",
            "leverage",
            "snapshot_timestamp_utc",
            "provenance",
            "account_scope_id",
        }
        self.assertTrue(self.template["account_snapshots"])
        for snapshot in self.template["account_snapshots"]:
            self.assertTrue(required.issubset(snapshot))
            for field in ("login_account_alias", "server", "account_scope_id"):
                self.assertTrue(str(snapshot[field]).startswith("SANITIZED_"))

    def test_request_and_result_fields(self):
        request = self.template["requests"][0]
        self.assertTrue(
            {
                "request_correlation_id",
                "application_order_id",
                "account_scope",
                "symbol",
                "side",
                "requested_volume",
                "order_type",
                "request_price",
                "requested_sl",
                "requested_tp",
                "magic",
                "comment",
                "request_timestamp_utc",
            }.issubset(request)
        )

        result = self.template["broker_results"][0]
        self.assertTrue(
            {
                "request_correlation_id",
                "retcode",
                "result",
                "bid",
                "ask",
                "comment",
                "request_id",
                "result_timestamp_utc",
                "account_scope",
            }.issubset(result)
        )
        self.assertTrue(
            {"order", "deal", "volume", "price"}.issubset(result["result"])
        )

    def test_before_and_after_positions_preserve_scope(self):
        for section in ("position_snapshots_before", "position_snapshots_after"):
            self.assertTrue(self.template[section])
            for position in self.template[section]:
                required = {
                    "position_ticket",
                    "symbol",
                    "type",
                    "volume",
                    "price_open",
                    "sl",
                    "tp",
                    "open_time_utc",
                    "magic",
                    "comment",
                    "account_scope",
                    "snapshot_timestamp_utc",
                    "source_sequence",
                }
                self.assertTrue(required.issubset(position))
                self.assertTrue(position["account_scope"].startswith("SANITIZED_"))

    def test_history_orders_and_independent_deals(self):
        order = self.template["history_orders"][0]
        self.assertTrue(
            {
                "order_ticket",
                "position_id",
                "symbol",
                "type",
                "state",
                "volume_initial",
                "volume_current",
                "time_setup_utc",
                "time_done_utc",
                "request_correlation_id",
                "account_scope",
                "retrieval_batch_id",
            }.issubset(order)
        )

        deals = self.template["history_deals"]
        self.assertGreaterEqual(len(deals), 2)
        tickets = []
        for deal in deals:
            self.assertTrue(
                {
                    "deal_ticket",
                    "order_ticket",
                    "position_id",
                    "entry_exit",
                    "symbol",
                    "volume",
                    "price",
                    "profit",
                    "commission",
                    "swap",
                    "fee",
                    "timestamp_utc",
                    "magic",
                    "comment",
                    "account_scope",
                    "source_sequence",
                    "retrieval_batch_id",
                }.issubset(deal)
            )
            tickets.append(deal["deal_ticket"])
        self.assertEqual(len(tickets), len(set(tickets)))
        self.assertTrue(all(ticket.startswith("SANITIZED_") for ticket in tickets))

    def test_retrieval_batches_and_cases(self):
        batch = self.template["retrieval_batches"][0]
        self.assertTrue(
            {
                "capture_id",
                "query_id",
                "query_type",
                "account_scope",
                "query_start_utc",
                "query_end_utc",
                "retrieval_timestamp_utc",
                "retrieval_sequence",
                "pagination_or_cursor",
                "returned_event_ids_in_returned_order",
                "returned_event_timestamps_in_returned_order",
                "event_payload_digests",
                "complete_response_digest",
                "overlap_with_previous_retrieval",
                "already_observed_flags",
            }.issubset(batch)
        )

        cases = self.template["case_matrix"]
        self.assertEqual({case["case_id"] for case in cases}, CASE_IDS)
        self.assertTrue(all(case["status"] in CASE_STATUSES for case in cases))

    def test_collision_and_activation_sections(self):
        collision = self.template["collision_analysis"][0]
        self.assertTrue(
            {
                "relation_id",
                "identity_type",
                "account_scope",
                "lifecycle_interval",
                "numeric_relation_token",
                "observed_equal_to",
                "observed_not_equal_to",
                "source_event_refs",
                "confidence",
            }.issubset(collision)
        )

        activation = self.template["activation_evidence"][0]
        self.assertTrue(
            {
                "module",
                "expected_role",
                "activation_status",
                "launcher_or_process_source",
                "startup_reference",
                "runtime_evidence_reference",
                "source_class",
                "confidence",
            }.issubset(activation)
        )

    def test_identifiers_are_sanitized_placeholders(self):
        for key, value in walk_strings(self.template):
            lowered_key = key.lower()
            lowered_value = str(value).lower()
            if any(marker in lowered_key or marker in lowered_value for marker in SECRET_MARKERS):
                self.assertIn(key, ALLOWED_SECRET_METADATA_KEYS)
            if any(
                identifier in lowered_key
                for identifier in (
                    "ticket",
                    "account_scope",
                    "request_correlation",
                    "application_order_id",
                    "source_event_id",
                    "retrieval_batch_id",
                    "relation_id",
                    "numeric_relation_token",
                )
            ):
                if value is not None and not isinstance(value, bool):
                    self.assertTrue(
                        PLACEHOLDER_RE.search(str(value)),
                        msg=f"non-placeholder identity field: {key}={value}",
                    )

    def test_template_does_not_claim_real_evidence(self):
        self.assertEqual(
            self.template["manifest"]["source_class"],
            "TEMPLATE_ONLY_NOT_EVIDENCE",
        )
        self.assertTrue(
            all(case["status"] == "UNAVAILABLE" for case in self.template["case_matrix"])
        )

    def test_no_production_runtime_imports(self):
        source = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("MetaTrader5", source)
        self.assertNotIn("sqlite3", source)
        self.assertNotIn("trades.db", source)

    def test_template_is_json_only_and_has_no_obvious_secrets(self):
        raw = TEMPLATE_PATH.read_text(encoding="utf-8").lower()
        for marker in SECRET_MARKERS:
            self.assertNotIn(marker, raw)
        self.assertNotIn("REDACTED_LIVE_ACCOUNT", raw)
        self.assertNotIn("REDACTED_DEMO_ACCOUNT", raw)


if __name__ == "__main__":
    unittest.main()

