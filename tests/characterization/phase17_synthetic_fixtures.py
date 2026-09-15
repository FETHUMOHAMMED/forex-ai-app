"""Synthetic-only Phase 17 validator fixtures.

These records are deliberately not broker evidence. They exercise reference,
scope, lineage, ordering, and collision mechanics only.
"""

from copy import deepcopy

from packages.evidence.phase17_evidence import (
    CASE_IDS,
    SANITIZED_RECORDED_RESPONSE,
    SANITIZED_SYNTHETIC_REPLAY,
)


SOURCE = SANITIZED_SYNTHETIC_REPLAY
PROVENANCE = "SANITIZED_SYNTHETIC_PROVENANCE_001"
SCOPE_A = "SANITIZED_SCOPE_A"
SCOPE_B = "SANITIZED_SCOPE_B"
SYMBOL = "SANITIZED_SYMBOL_EURUSD"


def _stamp(second: int) -> str:
    return f"2026-01-01T00:00:{second:02d}Z"


def _record(**fields):
    fields.setdefault("source_class", SOURCE)
    fields.setdefault("provenance_reference", PROVENANCE)
    return fields


def _case(case_id, refs=None, status="CAPTURED"):
    return {"case_id": case_id, "status": status, "evidence_refs": list(refs or [])}


def _account(scope, server, alias, environment):
    return _record(
        broker="SANITIZED_BROKER",
        login_account_alias=alias,
        server=server,
        environment=environment,
        margin_account_mode="SANITIZED_MODE_EXAMPLE",
        margin_account_mode_source="SANITIZED_SYNTHETIC_SOURCE",
        margin_account_mode_verification_status="UNVERIFIED",
        currency="SANITIZED_CURRENCY",
        leverage="SANITIZED_LEVERAGE",
        snapshot_timestamp_utc=_stamp(0),
        provenance=PROVENANCE,
        account_scope_id=scope,
        completeness="SYNTHETIC_COMPLETE",
    )


def _request(request_id, app_id, scope, second, volume):
    return _record(
        request_correlation_id=request_id,
        application_order_id=app_id,
        account_scope=scope,
        symbol=SYMBOL,
        side="BUY",
        requested_volume=volume,
        order_type="SANITIZED_ORDER_TYPE",
        request_price=1.1,
        requested_sl=1.0,
        requested_tp=1.2,
        magic="SANITIZED_MAGIC",
        comment="SANITIZED_COMMENT",
        request_timestamp_utc=_stamp(second),
        source_sequence=f"SANITIZED_REQUEST_SEQUENCE_{second:03d}",
    )


def _result(request_id, scope, second, order, deal):
    return _record(
        request_correlation_id=request_id,
        retcode="SANITIZED_RETCODE_OK",
        result={"order": order, "deal": deal, "volume": 1, "price": 1.1},
        bid=1.09,
        ask=1.1,
        comment="SANITIZED_RESULT_COMMENT",
        request_id=f"SANITIZED_REQUEST_ID_{second:03d}",
        result_timestamp_utc=_stamp(second),
        account_scope=scope,
        source_sequence=f"SANITIZED_RESULT_SEQUENCE_{second:03d}",
    )


def _position(snapshot_id, ticket, scope, second, volume):
    return _record(
        snapshot_id=snapshot_id,
        request_correlation_id="SANITIZED_REQUEST_001",
        position_ticket=ticket,
        symbol=SYMBOL,
        type="BUY",
        volume=volume,
        price_open=1.1,
        sl=1.0,
        tp=1.2,
        open_time_utc=_stamp(6),
        magic="SANITIZED_MAGIC",
        comment="SANITIZED_COMMENT",
        account_scope=scope,
        snapshot_timestamp_utc=_stamp(second),
        source_sequence=f"SANITIZED_POSITION_SEQUENCE_{second:03d}",
    )


def _order(ticket, position, request, scope, second):
    return _record(
        order_ticket=ticket,
        position_id=position,
        symbol=SYMBOL,
        type="BUY",
        state="FILLED",
        volume_initial=100,
        volume_current=99,
        time_setup_utc=_stamp(second),
        time_done_utc=_stamp(second + 1),
        request_correlation_id=request,
        application_order_id=f"SANITIZED_APP_{ticket}",
        magic="SANITIZED_MAGIC",
        comment="SANITIZED_COMMENT",
        account_scope=scope,
        source_sequence=f"SANITIZED_ORDER_SEQUENCE_{second:03d}",
        retrieval_batch_id="SANITIZED_BATCH_001",
    )


def _deal(deal, order, position, entry_exit, scope, second, volume, event_id, sequence, batch):
    return _record(
        deal_ticket=deal,
        order_ticket=order,
        position_id=position,
        entry_exit=entry_exit,
        symbol=SYMBOL,
        volume=volume,
        price=1.1,
        profit=0,
        commission=0,
        swap=0,
        fee=0,
        timestamp_utc=_stamp(second),
        magic="SANITIZED_MAGIC",
        comment="SANITIZED_COMMENT",
        account_scope=scope,
        source_sequence=sequence,
        retrieval_batch_id=batch,
        source_event_id=event_id,
    )


def _retrieval(sequence, second, event_ids, overlap, flags):
    return _record(
        capture_id="SANITIZED_SYNTHETIC_CAPTURE_001",
        query_id="SANITIZED_QUERY_001",
        query_type="SANITIZED_HISTORY_DEALS",
        account_scope=SCOPE_A,
        query_start_utc=_stamp(0),
        query_end_utc=_stamp(30),
        retrieval_timestamp_utc=_stamp(second),
        retrieval_sequence=sequence,
        pagination_or_cursor=f"SANITIZED_CURSOR_{sequence}",
        returned_event_ids_in_returned_order=event_ids,
        returned_event_timestamps_in_returned_order=[_stamp(4), _stamp(10)],
        event_payload_digests=["SANITIZED_DIGEST_001", "SANITIZED_DIGEST_004"],
        complete_response_digest=f"SANITIZED_RESPONSE_DIGEST_{sequence}",
        overlap_with_previous_retrieval=overlap,
        already_observed_flags=flags,
        completeness="SYNTHETIC_COMPLETE",
    )


def build_synthetic_bundle() -> dict:
    """Build a complete-looking synthetic replay for validator mechanics only."""

    bundle = {
        "manifest": {
            "capture_id": "SANITIZED_SYNTHETIC_CAPTURE_001",
            "source_class": SOURCE,
            "collector_tool_version": "SANITIZED_SYNTHETIC_FIXTURE_2",
            "source_system": "SANITIZED_SYNTHETIC_SOURCE",
            "broker": "SANITIZED_BROKER",
            "account_scope": SCOPE_A,
            "server_scope": "SANITIZED_SERVER_A",
            "environment": "DEMO",
            "capture_start_utc": _stamp(0),
            "capture_end_utc": _stamp(29),
            "retrieval_windows": ["SANITIZED_WINDOW_001"],
            "pagination_information": "SANITIZED_PAGINATION",
            "completeness_declaration": "SYNTHETIC_COMPLETE_FOR_VALIDATOR",
            "sanitization_method": "SYNTHETIC_PLACEHOLDERS",
            "credential_secret_removal_confirmed": True,
            "historical_export_vs_recorded_response_vs_synthetic_replay": "SYNTHETIC_REPLAY",
            "immutable_after_collection": True,
            "provenance_reference": PROVENANCE,
            "reviewer_status": "SYNTHETIC_TEST_ONLY",
            "provenance_verification_status": "UNVERIFIED",
        },
        "account_snapshots": [
            _account(SCOPE_A, "SANITIZED_SERVER_A", "SANITIZED_ACCOUNT_A", "DEMO"),
            _account(SCOPE_B, "SANITIZED_SERVER_B", "SANITIZED_ACCOUNT_B", "TEST"),
        ],
        "requests": [
            _request("SANITIZED_REQUEST_001", "SANITIZED_APP_001", SCOPE_A, 2, 100),
            _request("SANITIZED_REQUEST_002", "SANITIZED_APP_002", SCOPE_B, 3, 20),
            _request("SANITIZED_REQUEST_003", "SANITIZED_APP_003", SCOPE_A, 14, 5),
        ],
        "broker_results": [
            _result("SANITIZED_REQUEST_001", SCOPE_A, 4, "SANITIZED_ORDER_001", "SANITIZED_DEAL_001"),
            _result("SANITIZED_REQUEST_002", SCOPE_B, 5, "SANITIZED_ORDER_002", "SANITIZED_DEAL_002"),
            _result("SANITIZED_REQUEST_003", SCOPE_A, 15, "SANITIZED_ORDER_004", "SANITIZED_DEAL_006"),
        ],
        "position_snapshots_before": [
            _position("SANITIZED_BEFORE_001", "SANITIZED_POSITION_001", SCOPE_A, 7, 10),
            _position("SANITIZED_BEFORE_002", "SANITIZED_POSITION_002", SCOPE_A, 9, 10),
        ],
        "position_snapshots_after": [
            _position("SANITIZED_AFTER_001", "SANITIZED_POSITION_001", SCOPE_A, 10, 5),
            _position("SANITIZED_AFTER_002", "SANITIZED_POSITION_002", SCOPE_A, 11, 0),
            _position("SANITIZED_AFTER_003", "SANITIZED_POSITION_003", SCOPE_A, 13, 2),
        ],
        "history_orders": [
            _order("SANITIZED_ORDER_001", "SANITIZED_POSITION_001", "SANITIZED_REQUEST_001", SCOPE_A, 2),
            _order("SANITIZED_ORDER_002", "SANITIZED_POSITION_004", "SANITIZED_REQUEST_002", SCOPE_B, 3),
            _order("SANITIZED_ORDER_003", "SANITIZED_POSITION_001", "SANITIZED_REQUEST_001", SCOPE_A, 10),
            _order("SANITIZED_ORDER_004", "SANITIZED_POSITION_005", "SANITIZED_REQUEST_003", SCOPE_A, 14),
        ],
        "history_deals": [
            _deal("SANITIZED_DEAL_001", "SANITIZED_ORDER_001", "SANITIZED_POSITION_001", "ENTRY", SCOPE_A, 4, 1, "SANITIZED_EVENT_001", "SANITIZED_DEAL_SEQUENCE_001", "SANITIZED_BATCH_001"),
            _deal("SANITIZED_DEAL_002", "SANITIZED_ORDER_002", "SANITIZED_POSITION_004", "ENTRY", SCOPE_B, 5, 6, "SANITIZED_EVENT_002", "SANITIZED_DEAL_SEQUENCE_002", "SANITIZED_BATCH_001"),
            _deal("SANITIZED_DEAL_003", "SANITIZED_ORDER_002", "SANITIZED_POSITION_004", "ENTRY", SCOPE_B, 6, 4, "SANITIZED_EVENT_003", "SANITIZED_DEAL_SEQUENCE_003", "SANITIZED_BATCH_001"),
            _deal("SANITIZED_DEAL_004", "SANITIZED_ORDER_003", "SANITIZED_POSITION_001", "EXIT", SCOPE_A, 10, 5, "SANITIZED_EVENT_004", "SANITIZED_DEAL_SEQUENCE_004", "SANITIZED_BATCH_002"),
            _deal("SANITIZED_DEAL_005", "SANITIZED_ORDER_003", "SANITIZED_POSITION_002", "EXIT", SCOPE_A, 11, 10, "SANITIZED_EVENT_005", "SANITIZED_DEAL_SEQUENCE_005", "SANITIZED_BATCH_002"),
            _deal("SANITIZED_DEAL_006", "SANITIZED_ORDER_004", "SANITIZED_POSITION_005", "ENTRY", SCOPE_A, 15, 5, "SANITIZED_EVENT_006", "SANITIZED_DEAL_SEQUENCE_006", "SANITIZED_BATCH_003"),
            _deal("SANITIZED_DEAL_001", "SANITIZED_ORDER_001", "SANITIZED_POSITION_001", "ENTRY", SCOPE_A, 4, 1, "SANITIZED_EVENT_001", "SANITIZED_DEAL_SEQUENCE_007", "SANITIZED_BATCH_002"),
        ],
        "retrieval_batches": [
            _retrieval("SANITIZED_RETRIEVAL_001", 20, ["SANITIZED_EVENT_001", "SANITIZED_EVENT_004"], [], [False, False]),
            _retrieval("SANITIZED_RETRIEVAL_002", 21, ["SANITIZED_EVENT_001", "SANITIZED_EVENT_004"], ["SANITIZED_EVENT_001", "SANITIZED_EVENT_004"], [True, True]),
        ],
        "case_matrix": [
            _case(CASE_IDS[0], [_ref for _ref in ("requests:SANITIZED_REQUEST_001", "broker_results:SANITIZED_REQUEST_001", "history_orders:SANITIZED_ORDER_001", "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_001", "position_snapshots_after:SANITIZED_AFTER_001")]),
            _case(CASE_IDS[1], ["requests:SANITIZED_REQUEST_002", "broker_results:SANITIZED_REQUEST_002", "history_orders:SANITIZED_ORDER_002", "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_002", "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_003"]),
            _case(CASE_IDS[2], ["requests:SANITIZED_REQUEST_001", "history_orders:SANITIZED_ORDER_001", "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_001"]),
            _case(CASE_IDS[3], ["position_snapshots_before:SANITIZED_BEFORE_001", "position_snapshots_after:SANITIZED_AFTER_001", "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_004"]),
            _case(CASE_IDS[4], ["position_snapshots_before:SANITIZED_BEFORE_002", "position_snapshots_after:SANITIZED_AFTER_002", "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_005"]),
            _case(CASE_IDS[5], ["requests:SANITIZED_REQUEST_003", "history_orders:SANITIZED_ORDER_004", "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_005", "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_006"]),
            _case(CASE_IDS[6], ["account_snapshots:SANITIZED_SCOPE_A", "position_snapshots_after:SANITIZED_AFTER_001", "position_snapshots_after:SANITIZED_AFTER_003"], status="UNAVAILABLE"),
            _case(CASE_IDS[7], ["account_snapshots:SANITIZED_SCOPE_A", "account_snapshots:SANITIZED_SCOPE_B"]),
            _case(CASE_IDS[8], ["retrieval_batches:SANITIZED_RETRIEVAL_001", "retrieval_batches:SANITIZED_RETRIEVAL_002"]),
            _case(CASE_IDS[9], ["retrieval_batches:SANITIZED_RETRIEVAL_001", "retrieval_batches:SANITIZED_RETRIEVAL_002", "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_001", "history_deals:source_sequence=SANITIZED_DEAL_SEQUENCE_007"]),
        ],
        "collision_analysis": [
            _record(relation_id="SANITIZED_REL_001", identity_type="ORDER", account_scope=SCOPE_A, lifecycle_interval="SANITIZED_INTERVAL_001", numeric_relation_token="SANITIZED_NUMERIC_001", observed_equal_to=["SANITIZED_REL_002"], observed_not_equal_to=["SANITIZED_REL_003"], source_event_refs=["SANITIZED_EVENT_001"], confidence="SYNTHETIC_ONLY"),
            _record(relation_id="SANITIZED_REL_002", identity_type="POSITION", account_scope=SCOPE_B, lifecycle_interval="SANITIZED_INTERVAL_002", numeric_relation_token="SANITIZED_NUMERIC_001", observed_equal_to=["SANITIZED_REL_001"], observed_not_equal_to=["SANITIZED_REL_003"], source_event_refs=["SANITIZED_EVENT_002"], confidence="SYNTHETIC_ONLY"),
        ],
        "activation_evidence": [
            _record(module="SANITIZED_LEGACY_RUNTIME", expected_role="SANITIZED_ROLE", activation_status="UNKNOWN", launcher_or_process_source="SANITIZED_LAUNCHER", startup_reference="SANITIZED_STARTUP", runtime_evidence_reference="SANITIZED_RUNTIME", confidence="SYNTHETIC_ONLY", notes="SYNTHETIC ONLY"),
        ],
    }
    return deepcopy(bundle)


def _replace_source_class(value, source_class):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "source_class":
                value[key] = source_class
            else:
                _replace_source_class(child, source_class)
    elif isinstance(value, list):
        for child in value:
            _replace_source_class(child, source_class)


def application_evidence_bundle() -> dict:
    """A complete-looking recorded application bundle, never broker-eligible."""

    bundle = build_synthetic_bundle()
    _replace_source_class(bundle, SANITIZED_RECORDED_RESPONSE)
    bundle["manifest"]["historical_export_vs_recorded_response_vs_synthetic_replay"] = "RECORDED_RESPONSE"
    return bundle


def _ref(section, record_id):
    return f"{section}:{record_id}"
