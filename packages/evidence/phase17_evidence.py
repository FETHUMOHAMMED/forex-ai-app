"""Fail-closed, offline Phase 17 evidence boundaries.

This module validates only supplied, sanitized data. It has no capability to
acquire broker evidence and never initializes MT5, opens a database, performs
network I/O, or starts production code.

Structural validity is not broker authenticity. Provenance is deliberately
reported as UNVERIFIED, so broker_eligible is always false in this offline
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import copy
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from uuid import uuid4


# These are the classifications defined by the approved Phase 17 protocol.
SANITIZED_HISTORICAL_EXPORT = "SANITIZED_HISTORICAL_EXPORT"
SANITIZED_RECORDED_RESPONSE = "SANITIZED_RECORDED_RESPONSE"
SANITIZED_SYNTHETIC_REPLAY = "SANITIZED_SYNTHETIC_REPLAY"
TEMPLATE_ONLY_NOT_EVIDENCE = "TEMPLATE_ONLY_NOT_EVIDENCE"
PROTOCOL_SOURCE_CLASSES = frozenset(
    {
        SANITIZED_HISTORICAL_EXPORT,
        SANITIZED_RECORDED_RESPONSE,
        SANITIZED_SYNTHETIC_REPLAY,
        TEMPLATE_ONLY_NOT_EVIDENCE,
    }
)

CAPTURED = "CAPTURED"
NOT_OBSERVED = "NOT_OBSERVED"
UNAVAILABLE = "UNAVAILABLE"
UNKNOWN = "UNKNOWN"
CASE_STATUSES = frozenset({CAPTURED, NOT_OBSERVED, UNAVAILABLE})

RETRIEVAL_OVERLAP = "RETRIEVAL_OVERLAP"
DUPLICATE_SOURCE_EVENT = "DUPLICATE_SOURCE_EVENT"
REPLAY_OBSERVED = "REPLAY_OBSERVED"
REPLAY_NOT_PROVEN = "REPLAY_NOT_PROVEN"

CASE_IDS = (
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
)

SECTIONS = (
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
)

SECTION_ID_FIELDS = {
    "account_snapshots": "account_scope_id",
    "requests": "request_correlation_id",
    "broker_results": "request_correlation_id",
    "position_snapshots_before": "snapshot_id",
    "position_snapshots_after": "snapshot_id",
    "history_orders": "order_ticket",
    "history_deals": "deal_ticket",
    "retrieval_batches": "retrieval_sequence",
    "collision_analysis": "relation_id",
    "activation_evidence": "module",
}

MANIFEST_REQUIRED_FIELDS = (
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
)

REQUIRED_FIELDS: Mapping[str, Tuple[str, ...]] = {
    "account_snapshots": (
        "broker", "login_account_alias", "server", "environment",
        "margin_account_mode", "currency", "leverage",
        "snapshot_timestamp_utc", "provenance", "account_scope_id",
        "source_class",
    ),
    "requests": (
        "request_correlation_id", "application_order_id", "account_scope",
        "symbol", "side", "requested_volume", "order_type",
        "request_price", "requested_sl", "requested_tp", "magic", "comment",
        "request_timestamp_utc", "source_class", "source_sequence",
    ),
    "broker_results": (
        "request_correlation_id", "retcode", "result", "bid", "ask",
        "comment", "request_id", "result_timestamp_utc", "account_scope",
        "source_class", "source_sequence",
    ),
    "position_snapshots_before": (
        "snapshot_id", "position_ticket", "symbol", "type", "volume",
        "price_open", "sl", "tp", "open_time_utc", "magic", "comment",
        "account_scope", "snapshot_timestamp_utc", "source_sequence",
        "source_class",
    ),
    "position_snapshots_after": (
        "snapshot_id", "position_ticket", "symbol", "type", "volume",
        "price_open", "sl", "tp", "open_time_utc", "magic", "comment",
        "account_scope", "snapshot_timestamp_utc", "source_sequence",
        "source_class",
    ),
    "history_orders": (
        "order_ticket", "position_id", "symbol", "type", "state",
        "volume_initial", "volume_current", "time_setup_utc", "time_done_utc",
        "request_correlation_id", "account_scope", "source_sequence",
        "retrieval_batch_id", "source_class",
    ),
    "history_deals": (
        "deal_ticket", "order_ticket", "position_id", "entry_exit", "symbol",
        "volume", "price", "profit", "commission", "swap", "fee",
        "timestamp_utc", "magic", "comment", "account_scope", "source_sequence",
        "retrieval_batch_id", "source_class", "source_event_id",
    ),
    "retrieval_batches": (
        "capture_id", "query_id", "query_type", "account_scope",
        "query_start_utc", "query_end_utc", "retrieval_timestamp_utc",
        "retrieval_sequence", "pagination_or_cursor",
        "returned_event_ids_in_returned_order",
        "returned_event_timestamps_in_returned_order", "event_payload_digests",
        "complete_response_digest", "overlap_with_previous_retrieval",
        "already_observed_flags", "source_class", "completeness",
    ),
    "collision_analysis": (
        "relation_id", "identity_type", "account_scope", "lifecycle_interval",
        "numeric_relation_token", "observed_equal_to", "observed_not_equal_to",
        "source_event_refs", "confidence", "source_class",
    ),
    "activation_evidence": (
        "module", "expected_role", "activation_status",
        "launcher_or_process_source", "startup_reference",
        "runtime_evidence_reference", "source_class", "confidence", "notes",
    ),
}

TIMESTAMP_FIELDS = frozenset(
    {
        "capture_start_utc", "capture_end_utc", "snapshot_timestamp_utc",
        "request_timestamp_utc", "result_timestamp_utc", "open_time_utc",
        "time_setup_utc", "time_done_utc", "timestamp_utc",
        "retrieval_timestamp_utc", "query_start_utc", "query_end_utc",
    }
)

SANITIZED_ID_FIELDS = frozenset(
    {
        "account_scope", "account_scope_id", "login_account_alias", "server",
        "server_scope", "order_ticket", "position_ticket", "position_id",
        "deal_ticket", "request_correlation_id", "application_order_id",
        "request_id", "source_event_id", "capture_id", "query_id",
        "retrieval_batch_id", "snapshot_id", "retrieval_sequence", "relation_id",
        "observation_id", "event_identity", "first_seen_retrieval",
        "repeated_retrieval", "source_event_refs", "observed_equal_to",
        "observed_not_equal_to",
    }
)

SECRET_PATTERNS = (
    re.compile(r"(?i)(?:password|passwd|api[_-]?key|access[_-]?token|refresh[_-]?token)\s*[:=]"),
    re.compile(r"(?i)authorization\s*:\s*bearer\s+\S+"),
    re.compile(r"-----BEGIN [A-Z ]+-----"),
    re.compile(r"(?i)mt5[_-]?password\s*[:=]"),
)
SANITIZED_IDENTIFIER_RE = re.compile(r"^SANITIZED_[A-Z0-9]+(?:_[A-Z0-9]+)*$")


class EvidenceSafetyError(ValueError):
    """Raised when collection would violate the Phase 17 safety boundary."""


def _parse_utc(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _is_sanitized_identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(SANITIZED_IDENTIFIER_RE.fullmatch(value))


def _secret_value(value: Any) -> bool:
    return isinstance(value, str) and any(pattern.search(value) for pattern in SECRET_PATTERNS)


def _sanitization_errors(value: Any, path: str = "", field: Optional[str] = None) -> List[str]:
    errors: List[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = f"{path}.{key}" if path else str(key)
            if key_text != "credential_secret_removal_confirmed" and any(
                marker in key_text for marker in ("password", "passwd", "api_key", "access_token", "secret", "credential")
            ):
                errors.append(f"secret-like field name: {child_path}")
            errors.extend(_sanitization_errors(child, child_path, str(key)))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            if field in SANITIZED_ID_FIELDS and not _is_sanitized_identifier(child):
                errors.append(f"unsanitized identifier at {path}[{index}]")
            errors.extend(_sanitization_errors(child, f"{path}[{index}]", field))
    elif field in SANITIZED_ID_FIELDS and value is not None and not _is_sanitized_identifier(value):
        errors.append(f"unsanitized identifier at {path}")
    elif _secret_value(value):
        errors.append(f"secret-like value at {path}")
    return errors


def _scope(record: Mapping[str, Any]) -> Optional[str]:
    return record.get("account_scope") or record.get("account_scope_id")


def _record_id(section: str, record: Mapping[str, Any]) -> Optional[str]:
    field = SECTION_ID_FIELDS.get(section)
    value = record.get(field) if field else None
    return value if isinstance(value, str) else None


def _resolve_refs(bundle: Mapping[str, Any], refs: Sequence[Any]) -> Tuple[Dict[str, List[Mapping[str, Any]]], List[str]]:
    resolved: Dict[str, List[Mapping[str, Any]]] = {}
    errors: List[str] = []
    for reference in refs:
        if not isinstance(reference, str) or ":" not in reference:
            errors.append(f"invalid evidence reference: {reference!r}")
            continue
        section, record_id = reference.split(":", 1)
        if section not in SECTION_ID_FIELDS or not record_id:
            errors.append(f"unknown evidence reference: {reference}")
            continue
        selector_field = SECTION_ID_FIELDS[section]
        selector_value = record_id
        if "=" in record_id:
            selector_field, selector_value = record_id.split("=", 1)
            if selector_field not in {SECTION_ID_FIELDS[section], "source_sequence", "source_event_id"} or not selector_value:
                errors.append(f"invalid evidence selector: {reference}")
                continue
        matches = [
            record for record in bundle.get(section, []) or []
            if isinstance(record, Mapping) and record.get(selector_field) == selector_value
        ]
        if not matches:
            errors.append(f"unresolved evidence reference: {reference}")
            continue
        resolved.setdefault(section, []).extend(matches)
    return resolved, errors


def _numeric(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _same_scope(records: Sequence[Mapping[str, Any]]) -> bool:
    scopes = {_scope(record) for record in records}
    return None not in scopes and len(scopes) == 1


@dataclass(frozen=True)
class EvidenceCollectionConfig:
    environment: str
    authorization_confirmed: bool
    broker: str
    server_scope: str
    account_scope: str
    collection_mode: str = "READ_ONLY"
    controlled_trade_authorized: bool = False
    cleanup_authorized: bool = False
    source_system: str = "SANITIZED_SOURCE_SYSTEM"
    collector_tool_version: str = "phase17-offline-collector-2"


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    broker_evidence_eligible: bool
    provenance_status: str
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    case_results: Mapping[str, str]
    replay_status: str


class OfflineEvidenceCollector:
    """Create an in-memory, explicitly authorized observation session.

    It accepts records supplied by a future collector but has no acquisition
    capability. Finalization seals internal state; callers receive defensive
    copies and cannot mutate the sealed session.
    """

    def __init__(self, config: EvidenceCollectionConfig):
        self.config = config
        self._validate_config()
        self.capture_id = f"SANITIZED_CAPTURE_{uuid4().hex[:12].upper()}"
        self._finalized = False
        self._bundle: Dict[str, Any] = self._new_bundle()
        self._sealed_bundle: Optional[Dict[str, Any]] = None

    def _validate_config(self) -> None:
        environment = self.config.environment.strip().upper()
        if environment not in {"DEMO", "TEST", "VALIDATION"}:
            raise EvidenceSafetyError("environment must be explicitly DEMO, TEST, or VALIDATION")
        if not self.config.authorization_confirmed:
            raise EvidenceSafetyError("explicit account authorization is required")
        for name, value in (
            ("broker", self.config.broker),
            ("server_scope", self.config.server_scope),
            ("account_scope", self.config.account_scope),
        ):
            if not isinstance(value, str) or not value:
                raise EvidenceSafetyError(f"{name} is required")
        if not _is_sanitized_identifier(self.config.server_scope):
            raise EvidenceSafetyError("server_scope must be a strict sanitized alias")
        if not _is_sanitized_identifier(self.config.account_scope):
            raise EvidenceSafetyError("account_scope must be a strict sanitized alias")
        if any(delimiter in self.config.account_scope for delimiter in ("|", ",", ";")):
            raise EvidenceSafetyError("account_scope must identify exactly one scope")
        mode = self.config.collection_mode.strip().upper()
        if mode not in {"READ_ONLY", "CONTROLLED_TRADE"}:
            raise EvidenceSafetyError("collection_mode must be READ_ONLY or CONTROLLED_TRADE")
        if mode == "CONTROLLED_TRADE" and not self.config.controlled_trade_authorized:
            raise EvidenceSafetyError("controlled-trade authorization is required")
        if mode == "CONTROLLED_TRADE" and not self.config.cleanup_authorized:
            raise EvidenceSafetyError("cleanup authorization is required")

    def _new_bundle(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return {
            "manifest": {
                "capture_id": self.capture_id,
                "source_class": SANITIZED_RECORDED_RESPONSE,
                "collector_tool_version": self.config.collector_tool_version,
                "source_system": self.config.source_system,
                "broker": self.config.broker,
                "account_scope": self.config.account_scope,
                "server_scope": self.config.server_scope,
                "environment": self.config.environment.upper(),
                "capture_start_utc": now,
                "capture_end_utc": None,
                "retrieval_windows": [],
                "pagination_information": None,
                "completeness_declaration": "NOT_FINALIZED",
                "sanitization_method": "REQUIRED_BEFORE_SUBMISSION",
                "credential_secret_removal_confirmed": True,
                "historical_export_vs_recorded_response_vs_synthetic_replay": "RECORDED_RESPONSE",
                "immutable_after_collection": False,
                "provenance_reference": f"SANITIZED_PROVENANCE_{self.capture_id}",
                "reviewer_status": "UNREVIEWED",
                "provenance_verification_status": "UNVERIFIED",
            },
            **{section: [] for section in SECTIONS},
        }

    def add_record(self, section: str, record: Mapping[str, Any]) -> None:
        if self._finalized:
            raise EvidenceSafetyError("collection session is finalized")
        if section not in SECTIONS or section == "case_matrix":
            raise EvidenceSafetyError("collector accepts only observation records")
        copied = dict(record)
        copied.setdefault("source_class", self._bundle["manifest"]["source_class"])
        if copied["source_class"] != self._bundle["manifest"]["source_class"]:
            raise EvidenceSafetyError("record source_class must match the protocol manifest")
        copied.setdefault("provenance_reference", self._bundle["manifest"]["provenance_reference"])
        errors = _sanitization_errors(copied)
        if errors:
            raise EvidenceSafetyError("; ".join(errors))
        self._bundle[section].append(copied)

    def finalize(self, completeness: str = "COMPLETE_FOR_DECLARED_SCOPE") -> Dict[str, Any]:
        if self._finalized:
            raise EvidenceSafetyError("collection session is already finalized")
        self._bundle["manifest"]["capture_end_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._bundle["manifest"]["completeness_declaration"] = completeness
        self._bundle["manifest"]["immutable_after_collection"] = True
        self._sealed_bundle = copy.deepcopy(self._bundle)
        self._finalized = True
        return copy.deepcopy(self._sealed_bundle)

    def sealed_snapshot(self) -> Dict[str, Any]:
        if not self._finalized or self._sealed_bundle is None:
            raise EvidenceSafetyError("collection session is not finalized")
        return copy.deepcopy(self._sealed_bundle)


def _validate_timestamps(bundle: Mapping[str, Any], errors: List[str]) -> None:
    manifest = bundle.get("manifest", {})
    parsed_manifest: Dict[str, datetime] = {}
    for field in ("capture_start_utc", "capture_end_utc"):
        timestamp = _parse_utc(manifest.get(field))
        if timestamp is None:
            errors.append(f"manifest {field} is not timezone-aware ISO-8601")
        else:
            parsed_manifest[field] = timestamp
    if parsed_manifest.get("capture_start_utc") and parsed_manifest.get("capture_end_utc"):
        if parsed_manifest["capture_start_utc"] > parsed_manifest["capture_end_utc"]:
            errors.append("capture_start_utc must not be after capture_end_utc")
    for section in SECTIONS:
        for index, record in enumerate(bundle.get(section, []) or []):
            if not isinstance(record, Mapping):
                continue
            for field, value in record.items():
                if field in TIMESTAMP_FIELDS and _parse_utc(value) is None:
                    errors.append(f"{section}[{index}].{field} is not timezone-aware ISO-8601")


def _case_scoped_status(case_id: str, bundle: Mapping[str, Any], case: Mapping[str, Any], errors: List[str]) -> Tuple[str, str]:
    resolved, ref_errors = _resolve_refs(bundle, case.get("evidence_refs", []))
    if ref_errors:
        errors.extend(f"{case_id}: {item}" for item in ref_errors)
        return UNAVAILABLE, REPLAY_NOT_PROVEN
    records = [record for section_records in resolved.values() for record in section_records]
    if case_id != "CASE_08_TWO_ACCOUNT_SERVER_SCOPES" and not _same_scope(records):
        errors.append(f"{case_id}: references must belong to one account scope")
        return UNAVAILABLE, REPLAY_NOT_PROVEN

    requests = resolved.get("requests", [])
    results = resolved.get("broker_results", [])
    orders = resolved.get("history_orders", [])
    deals = resolved.get("history_deals", [])
    before = resolved.get("position_snapshots_before", [])
    after = resolved.get("position_snapshots_after", [])
    retrievals = resolved.get("retrieval_batches", [])
    accounts = resolved.get("account_snapshots", [])

    if case_id == CASE_IDS[0]:
        ok = len(requests) == len(results) == len(orders) == len(deals) == len(after) == 1
        ok = ok and deals[0].get("entry_exit") == "ENTRY" and deals[0].get("order_ticket") == orders[0].get("order_ticket")
        ok = ok and deals[0].get("position_id") == after[0].get("position_ticket")
        ok = ok and results[0].get("request_correlation_id") == requests[0].get("request_correlation_id")
        return (CAPTURED, REPLAY_NOT_PROVEN) if ok else (UNAVAILABLE, REPLAY_NOT_PROVEN)
    if case_id == CASE_IDS[1]:
        ok = len(orders) == 1 and len(deals) >= 2 and all(d.get("entry_exit") == "ENTRY" for d in deals)
        ok = ok and len({d.get("deal_ticket") for d in deals}) == len(deals)
        ok = ok and all(d.get("order_ticket") == orders[0].get("order_ticket") for d in deals)
        return (CAPTURED, REPLAY_NOT_PROVEN) if ok else (UNAVAILABLE, REPLAY_NOT_PROVEN)
    if case_id == CASE_IDS[2]:
        requested = _numeric(requests[0].get("requested_volume")) if len(requests) == 1 else None
        executed = sum((_numeric(d.get("volume")) or 0.0) for d in deals if d.get("entry_exit") == "ENTRY")
        ok = len(requests) == len(orders) == 1 and requested is not None and 0 < executed < requested
        ok = ok and all(d.get("order_ticket") == orders[0].get("order_ticket") for d in deals)
        return (CAPTURED, REPLAY_NOT_PROVEN) if ok else (UNAVAILABLE, REPLAY_NOT_PROVEN)
    if case_id in {CASE_IDS[3], CASE_IDS[4]}:
        ok = len(before) == len(after) == 1 and bool(deals) and all(d.get("entry_exit") == "EXIT" for d in deals)
        if ok:
            before_volume = _numeric(before[0].get("volume"))
            after_volume = _numeric(after[0].get("volume"))
            ok = before_volume is not None and after_volume is not None
            if case_id == CASE_IDS[3]:
                ok = ok and before_volume > after_volume > 0
            else:
                ok = ok and before_volume > 0 and after_volume == 0
            ok = ok and all(d.get("position_id") == before[0].get("position_ticket") for d in deals)
        return (CAPTURED, REPLAY_NOT_PROVEN) if ok else (UNAVAILABLE, REPLAY_NOT_PROVEN)
    if case_id == CASE_IDS[5]:
        if not (len(deals) >= 2 and any(d.get("entry_exit") == "EXIT" for d in deals) and any(d.get("entry_exit") == "ENTRY" for d in deals)):
            return UNAVAILABLE, REPLAY_NOT_PROVEN
        close_times = [_parse_utc(d.get("timestamp_utc")) for d in deals if d.get("entry_exit") == "EXIT"]
        reopen_times = [_parse_utc(d.get("timestamp_utc")) for d in deals if d.get("entry_exit") == "ENTRY"]
        ok = all(close_times) and all(reopen_times) and max(close_times) < min(reopen_times)
        ok = ok and len({d.get("position_id") for d in deals}) >= 2
        return (CAPTURED, REPLAY_NOT_PROVEN) if ok else (UNAVAILABLE, REPLAY_NOT_PROVEN)
    if case_id == CASE_IDS[6]:
        mode_verified = any(
            account.get("margin_account_mode_verification_status") == "VERIFIED"
            and account.get("margin_account_mode_source") in {"AUTHORITATIVE_ACCOUNT_SNAPSHOT", "AUTHORITATIVE_BROKER_EXPORT"}
            for account in accounts
        )
        symbols = {position.get("symbol") for position in after}
        ok = len(after) >= 2 and len(symbols) == 1 and mode_verified
        return (CAPTURED, REPLAY_NOT_PROVEN) if ok else (UNAVAILABLE, REPLAY_NOT_PROVEN)
    if case_id == CASE_IDS[7]:
        scopes = {account.get("account_scope_id") for account in accounts}
        servers = {account.get("server") for account in accounts}
        ok = len(accounts) >= 2 and len(scopes) >= 2 and len(servers) >= 2
        return (CAPTURED, REPLAY_NOT_PROVEN) if ok else (UNAVAILABLE, REPLAY_NOT_PROVEN)
    if case_id == CASE_IDS[8]:
        if len(retrievals) < 2:
            return UNAVAILABLE, REPLAY_NOT_PROVEN
        query_keys = {(r.get("query_id"), r.get("account_scope"), r.get("query_start_utc"), r.get("query_end_utc")) for r in retrievals}
        retrieval_times = [_parse_utc(r.get("retrieval_timestamp_utc")) for r in retrievals]
        arrays_ok = all(
            len(r.get("returned_event_ids_in_returned_order", []))
            == len(r.get("returned_event_timestamps_in_returned_order", []))
            == len(r.get("event_payload_digests", []))
            == len(r.get("already_observed_flags", []))
            for r in retrievals
        )
        ok = len(query_keys) == 1 and all(retrieval_times[i] < retrieval_times[i + 1] for i in range(len(retrieval_times) - 1)) and arrays_ok
        overlap = any(r.get("overlap_with_previous_retrieval") for r in retrievals)
        return (CAPTURED, RETRIEVAL_OVERLAP if overlap else REPLAY_NOT_PROVEN) if ok else (UNAVAILABLE, REPLAY_NOT_PROVEN)
    if case_id == CASE_IDS[9]:
        source_events = [d.get("source_event_id") for d in deals if d.get("source_event_id")]
        duplicate_event = len(source_events) != len(set(source_events))
        overlap = any(r.get("overlap_with_previous_retrieval") for r in retrievals)
        if duplicate_event:
            return CAPTURED, DUPLICATE_SOURCE_EVENT
        if overlap:
            errors.append(f"{case_id}: retrieval overlap does not prove replay")
            return UNAVAILABLE, RETRIEVAL_OVERLAP
        return UNAVAILABLE, REPLAY_NOT_PROVEN
    return UNAVAILABLE, REPLAY_NOT_PROVEN


def validate_evidence_bundle(bundle: Mapping[str, Any]) -> ValidationReport:
    """Validate structure and relationships without certifying authenticity."""

    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(bundle, Mapping):
        return ValidationReport(False, False, "UNVERIFIED", ("bundle must be a mapping",), (), {}, REPLAY_NOT_PROVEN)
    manifest = bundle.get("manifest")
    if not isinstance(manifest, Mapping):
        errors.append("manifest is required")
        manifest = {}
    for section in SECTIONS:
        if not isinstance(bundle.get(section), list):
            errors.append(f"required section missing or not a list: {section}")
    for field in MANIFEST_REQUIRED_FIELDS:
        if field not in manifest:
            errors.append(f"manifest missing: {field}")
    source_class = manifest.get("source_class")
    if source_class not in PROTOCOL_SOURCE_CLASSES:
        errors.append("manifest source_class is not protocol-aligned")
    for field in ("capture_id", "account_scope", "server_scope", "provenance_reference"):
        if field in manifest and not _is_sanitized_identifier(manifest[field]):
            errors.append(f"manifest {field} is not a strict sanitized identifier")
    if str(manifest.get("environment", "")).upper() not in {"DEMO", "TEST", "VALIDATION"}:
        errors.append("environment must be explicitly DEMO, TEST, or VALIDATION")
    if manifest.get("credential_secret_removal_confirmed") is not True:
        errors.append("credential_secret_removal_confirmed must be true")
    errors.extend(_sanitization_errors(bundle))
    _validate_timestamps(bundle, errors)

    all_source_sequences: List[str] = []
    for section, fields in REQUIRED_FIELDS.items():
        for index, record in enumerate(bundle.get(section, []) or []):
            if not isinstance(record, Mapping):
                errors.append(f"{section}[{index}] is not an object")
                continue
            missing = [field for field in fields if field not in record]
            if missing:
                errors.append(f"{section}[{index}] missing: {', '.join(missing)}")
            if section != "case_matrix" and not (record.get("provenance") or record.get("provenance_reference")):
                errors.append(f"{section}[{index}] missing provenance")
            if record.get("source_class") != source_class:
                errors.append(f"{section}[{index}] source_class does not match manifest")
            if record.get("source_sequence") is not None:
                all_source_sequences.append(str(record.get("source_sequence")))
    if len(all_source_sequences) != len(set(all_source_sequences)):
        errors.append("source_sequence values must be unique across the capture")

    case_map: Dict[str, Mapping[str, Any]] = {}
    for case in bundle.get("case_matrix", []) or []:
        if not isinstance(case, Mapping):
            errors.append("case_matrix entries must be objects")
            continue
        case_id = case.get("case_id")
        if case_id in case_map:
            errors.append(f"duplicate lifecycle case ID: {case_id}")
        case_map[case_id] = case
    case_results: Dict[str, str] = {}
    replay_status = REPLAY_NOT_PROVEN
    for case_id in CASE_IDS:
        case = case_map.get(case_id)
        if case is None:
            case_results[case_id] = UNAVAILABLE
            warnings.append(f"{case_id}: missing case declaration")
            continue
        status = case.get("status")
        if status not in CASE_STATUSES:
            errors.append(f"{case_id}: invalid status")
            case_results[case_id] = UNAVAILABLE
            continue
        if status != CAPTURED:
            case_results[case_id] = status
            continue
        refs = case.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{case_id}: CAPTURED requires evidence_refs")
            case_results[case_id] = UNAVAILABLE
            continue
        result, case_replay_status = _case_scoped_status(case_id, bundle, case, errors)
        case_results[case_id] = result
        if result != CAPTURED:
            errors.append(f"{case_id}: CAPTURED case did not satisfy its scoped evidence requirements")
        if case_id == CASE_IDS[9]:
            replay_status = case_replay_status

    provenance_status = "UNVERIFIED"
    warnings.append("broker provenance is UNVERIFIED; offline validation cannot certify authenticity")
    return ValidationReport(
        valid=not errors,
        broker_evidence_eligible=False,
        provenance_status=provenance_status,
        errors=tuple(errors),
        warnings=tuple(warnings),
        case_results=case_results,
        replay_status=replay_status,
    )
