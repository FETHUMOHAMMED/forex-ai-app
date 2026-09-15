"""Adversarial offline tests for the Phase 17 evidence boundary."""

import ast
import copy
import json
import unittest
from pathlib import Path

from packages.evidence.phase17_evidence import (
    CASE_IDS,
    EvidenceCollectionConfig,
    EvidenceSafetyError,
    OfflineEvidenceCollector,
    RETRIEVAL_OVERLAP,
    SANITIZED_HISTORICAL_EXPORT,
    SANITIZED_RECORDED_RESPONSE,
    SANITIZED_SYNTHETIC_REPLAY,
    DUPLICATE_SOURCE_EVENT,
    UNAVAILABLE,
    validate_evidence_bundle,
)
from tests.characterization.phase17_synthetic_fixtures import (
    application_evidence_bundle,
    build_synthetic_bundle,
)


ROOT = Path(__file__).resolve().parents[2]


def _config(**overrides):
    values = {
        "environment": "DEMO",
        "authorization_confirmed": True,
        "broker": "SANITIZED_BROKER",
        "server_scope": "SANITIZED_SERVER",
        "account_scope": "SANITIZED_ACCOUNT",
    }
    values.update(overrides)
    return EvidenceCollectionConfig(**values)


class Phase17EvidencePipelineTests(unittest.TestCase):
    @staticmethod
    def _replace_source_class(value, source_class):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "source_class":
                    value[key] = source_class
                else:
                    Phase17EvidencePipelineTests._replace_source_class(child, source_class)
        elif isinstance(value, list):
            for child in value:
                Phase17EvidencePipelineTests._replace_source_class(child, source_class)

    def test_complete_synthetic_fixture_is_validated_but_never_broker_eligible(self):
        report = validate_evidence_bundle(build_synthetic_bundle())
        self.assertTrue(report.valid, report.errors)
        self.assertFalse(report.broker_evidence_eligible)
        self.assertEqual(report.provenance_status, "UNVERIFIED")
        self.assertEqual(report.case_results[CASE_IDS[6]], UNAVAILABLE)
        self.assertEqual(report.case_results[CASE_IDS[9]], "CAPTURED")
        self.assertEqual(report.replay_status, DUPLICATE_SOURCE_EVENT)

    def test_application_evidence_cannot_be_promoted_to_broker_evidence(self):
        report = validate_evidence_bundle(application_evidence_bundle())
        self.assertTrue(report.valid, report.errors)
        self.assertFalse(report.broker_evidence_eligible)

    def test_relabelled_synthetic_data_stays_unverified(self):
        bundle = build_synthetic_bundle()
        self._replace_source_class(bundle, SANITIZED_HISTORICAL_EXPORT)
        report = validate_evidence_bundle(bundle)
        self.assertTrue(report.valid, report.errors)
        self.assertFalse(report.broker_evidence_eligible)
        self.assertEqual(report.provenance_status, "UNVERIFIED")

    def test_fake_evidence_reference_fails_closed(self):
        bundle = build_synthetic_bundle()
        bundle["case_matrix"][0]["evidence_refs"] = ["history_deals:SANITIZED_DOES_NOT_EXIST"]
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)
        self.assertEqual(report.case_results[CASE_IDS[0]], UNAVAILABLE)

    def test_missing_case_is_unavailable_not_pass(self):
        bundle = build_synthetic_bundle()
        bundle["case_matrix"] = bundle["case_matrix"][:-1]
        report = validate_evidence_bundle(bundle)
        self.assertEqual(report.case_results[CASE_IDS[9]], UNAVAILABLE)
        self.assertFalse(report.broker_evidence_eligible)

    def test_captured_case_without_references_fails_closed(self):
        bundle = build_synthetic_bundle()
        bundle["case_matrix"][0]["evidence_refs"] = []
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)

    def test_cross_scope_reference_fails_closed(self):
        bundle = build_synthetic_bundle()
        bundle["case_matrix"][0]["evidence_refs"].append("history_orders:SANITIZED_ORDER_002")
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)

    def test_duplicate_case_id_fails_closed(self):
        bundle = build_synthetic_bundle()
        bundle["case_matrix"].append(copy.deepcopy(bundle["case_matrix"][0]))
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)
        self.assertTrue(any("duplicate lifecycle case ID" in error for error in report.errors))

    def test_invalid_and_timezone_less_timestamps_fail_closed(self):
        for timestamp in ("not-a-timestamp", "2026-01-01T00:00:00"):
            with self.subTest(timestamp=timestamp):
                bundle = build_synthetic_bundle()
                bundle["manifest"]["capture_start_utc"] = timestamp
                report = validate_evidence_bundle(bundle)
                self.assertFalse(report.valid)

    def test_reversed_capture_timestamps_fail_closed(self):
        bundle = build_synthetic_bundle()
        bundle["manifest"]["capture_start_utc"] = "2026-01-01T00:00:29Z"
        bundle["manifest"]["capture_end_utc"] = "2026-01-01T00:00:01Z"
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)

    def test_invalid_retrieval_order_fails_closed(self):
        bundle = build_synthetic_bundle()
        bundle["retrieval_batches"][1]["retrieval_timestamp_utc"] = "2026-01-01T00:00:19Z"
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)

    def test_fake_account_mode_cannot_capture_multiple_position_case(self):
        bundle = build_synthetic_bundle()
        bundle["case_matrix"][6]["status"] = "CAPTURED"
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)
        self.assertEqual(report.case_results[CASE_IDS[6]], UNAVAILABLE)

    def test_claimed_provenance_verification_is_not_trusted(self):
        bundle = build_synthetic_bundle()
        bundle["manifest"]["provenance_verification_status"] = "VERIFIED"
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.broker_evidence_eligible)
        self.assertEqual(report.provenance_status, "UNVERIFIED")

    def test_duplicate_source_sequence_fails_closed(self):
        bundle = build_synthetic_bundle()
        bundle["requests"][1]["source_sequence"] = bundle["requests"][0]["source_sequence"]
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)

    def test_retrieval_overlap_is_not_replay(self):
        bundle = build_synthetic_bundle()
        bundle["case_matrix"][9]["evidence_refs"] = [
            "retrieval_batches:SANITIZED_RETRIEVAL_001",
            "retrieval_batches:SANITIZED_RETRIEVAL_002",
        ]
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)
        self.assertEqual(report.replay_status, RETRIEVAL_OVERLAP)

    def test_nested_and_free_form_secret_values_fail_closed(self):
        bundle = build_synthetic_bundle()
        bundle["requests"][0]["comment"] = "Authorization: Bearer SANITIZED_SHOULD_NOT_PASS"
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)

    def test_two_aliases_with_one_scope_do_not_count_as_two_scopes(self):
        bundle = build_synthetic_bundle()
        bundle["account_snapshots"][1]["account_scope_id"] = "SANITIZED_SCOPE_A"
        bundle["account_snapshots"][1]["server"] = "SANITIZED_SERVER_A"
        bundle["case_matrix"][7]["evidence_refs"] = [
            "account_snapshots:SANITIZED_SCOPE_A",
            "account_snapshots:SANITIZED_SCOPE_A",
        ]
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)
        self.assertEqual(report.case_results[CASE_IDS[7]], UNAVAILABLE)

    def test_unrelated_records_cannot_satisfy_case_one(self):
        bundle = build_synthetic_bundle()
        bundle["case_matrix"][0]["evidence_refs"] = [
            "requests:SANITIZED_REQUEST_001",
            "broker_results:SANITIZED_REQUEST_001",
            "history_orders:SANITIZED_ORDER_001",
            "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_004",
            "position_snapshots_after:SANITIZED_AFTER_001",
        ]
        report = validate_evidence_bundle(bundle)
        self.assertFalse(report.valid)

    def test_finalized_collection_returns_defensive_copy(self):
        collector = OfflineEvidenceCollector(_config())
        collector.add_record(
            "requests",
            {
                "request_correlation_id": "SANITIZED_REQUEST_001",
                "account_scope": "SANITIZED_ACCOUNT",
                "request_timestamp_utc": "2026-01-01T00:00:00Z",
                "source_sequence": "SANITIZED_SEQUENCE_001",
            },
        )
        returned = collector.finalize()
        returned["requests"].append({"source_class": SANITIZED_RECORDED_RESPONSE})
        self.assertEqual(len(collector.sealed_snapshot()["requests"]), 1)
        with self.assertRaises(EvidenceSafetyError):
            collector.add_record("requests", {})

    def test_collector_requires_safe_environment_authorization_and_scope(self):
        for environment in ("LIVE", "PRODUCTION", "UNKNOWN", "", "SANITIZED_ENVIRONMENT"):
            with self.subTest(environment=environment):
                with self.assertRaises(EvidenceSafetyError):
                    OfflineEvidenceCollector(_config(environment=environment))
        with self.assertRaises(EvidenceSafetyError):
            OfflineEvidenceCollector(_config(authorization_confirmed=False))
        with self.assertRaises(EvidenceSafetyError):
            OfflineEvidenceCollector(_config(account_scope="RAW_ACCOUNT"))
        with self.assertRaises(EvidenceSafetyError):
            OfflineEvidenceCollector(_config(server_scope="RAW_SERVER"))
        with self.assertRaises(EvidenceSafetyError):
            OfflineEvidenceCollector(_config(account_scope="SANITIZED_A|SANITIZED_B"))

    def test_controlled_trade_mode_requires_explicit_authorization_and_cleanup(self):
        with self.assertRaises(EvidenceSafetyError):
            OfflineEvidenceCollector(_config(collection_mode="CONTROLLED_TRADE"))
        with self.assertRaises(EvidenceSafetyError):
            OfflineEvidenceCollector(_config(collection_mode="CONTROLLED_TRADE", controlled_trade_authorized=True))

    def test_collector_rejects_secret_fields_and_mismatched_source_class(self):
        collector = OfflineEvidenceCollector(_config())
        with self.assertRaises(EvidenceSafetyError):
            collector.add_record("requests", {"password": "never-store"})
        with self.assertRaises(EvidenceSafetyError):
            collector.add_record("requests", {"source_class": SANITIZED_SYNTHETIC_REPLAY})

    def test_template_is_not_evidence(self):
        template = json.loads((ROOT / "docs/characterization/phase17_evidence_template.json").read_text(encoding="utf-8"))
        report = validate_evidence_bundle(template)
        self.assertFalse(report.broker_evidence_eligible)

    def test_protocol_source_classes_are_used(self):
        self.assertEqual(SANITIZED_SYNTHETIC_REPLAY, build_synthetic_bundle()["manifest"]["source_class"])
        self.assertEqual(SANITIZED_RECORDED_RESPONSE, application_evidence_bundle()["manifest"]["source_class"])

    def test_no_forbidden_runtime_dependencies_in_new_evidence_module(self):
        source = (ROOT / "packages/evidence/phase17_evidence.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in ("MetaTrader5", "sqlite3", "broker_exness", "auto_trader_exness", "requests", "urllib", "socket"):
            self.assertFalse(any(item == forbidden or item.startswith(forbidden + ".") for item in imports))


if __name__ == "__main__":
    unittest.main()
