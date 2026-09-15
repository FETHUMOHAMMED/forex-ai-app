# Phase 17 — Evidence Acquisition Protocol

## 1. Purpose and safety boundary

This protocol defines the non-production evidence contract required before the Phase 16 identity gate can progress.

It is an acquisition and review specification only. It does not:

- initialize MT5;
- connect to Exness or another broker;
- call a network service;
- submit, modify, close, or inspect live orders or positions;
- execute production trading code;
- access trades.db or another production database;
- modify the legacy trades.ticket field;
- define a canonical ticket mapping;
- infer netting/hedging from application configuration;
- infer namespace uniqueness from a finite sample;
- activate newer identity or reconciliation modules.

The accompanying JSON file is a structural template only. It is not evidence and contains no broker facts.

## 2. Evidence classifications

Every submitted capture must declare exactly one source class:

- SANITIZED_HISTORICAL_EXPORT — sanitized broker/MT5 history exported from a documented source.
- SANITIZED_RECORDED_RESPONSE — sanitized request/result/snapshot responses recorded without changing state.
- SANITIZED_SYNTHETIC_REPLAY — synthetic response replay used only to validate application handling.
- TEMPLATE_ONLY_NOT_EVIDENCE — the placeholder template in this phase.

These classes must not be silently promoted. Synthetic replay cannot establish broker facts. A finite historical sample cannot establish global identifier uniqueness.

Every reviewed finding must also carry one confidence classification:

- PROVEN
- STRONGLY INDICATED
- INFERRED
- UNKNOWN

Current Phase 16 UNKNOWN findings remain UNKNOWN until the required evidence is actually supplied.

## 3. Capture manifest

Every evidence bundle must contain one manifest with:

- capture_id;
- source_class;
- collector/tool name and version;
- source system;
- broker;
- account scope;
- server scope;
- environment;
- capture_start_utc;
- capture_end_utc;
- retrieval windows;
- pagination/cursor information;
- completeness declaration;
- sanitization method;
- credential_secret_removal_confirmed;
- historical_export_vs_recorded_response_vs_synthetic_replay;
- immutable_after_collection;
- source provenance reference;
- reviewer status.

The manifest must state whether the bundle is complete for its declared time window. A partial export must be labeled incomplete and cannot support conclusions about missing events.

The account and server values in a repository submission must be sanitized aliases. The bundle must preserve equality and inequality relationships across records.

## 4. Account snapshot schema

Each account snapshot must contain:

- broker;
- login_account_alias;
- server;
- environment;
- margin_account_mode;
- currency;
- leverage;
- snapshot_timestamp_utc;
- provenance;
- account_scope_id;
- source_class;
- completeness.

The account snapshot must identify whether margin_account_mode came from an authoritative account snapshot, documented broker material, or is unavailable. Application flags such as hedge_mode_enabled and enable_partial_close are not substitutes.

The account-level scope identifier is a sanitized stable relation-preserving value. It is not a new production identity.

## 5. Trade request schema

Each request record must contain:

- request_correlation_id;
- application_order_id;
- account_scope;
- symbol;
- side;
- requested_volume;
- order_type;
- request_price;
- requested_sl;
- requested_tp;
- magic;
- comment;
- request_timestamp_utc;
- source_class;
- source_sequence.

The request correlation ID must be the identifier used to connect the application request with the recorded broker result and snapshots. It must not be invented after the fact.

## 6. Broker-result schema

Each broker result must contain:

- request_correlation_id;
- retcode;
- result.order;
- result.deal;
- result.volume;
- result.price;
- bid;
- ask;
- comment;
- request_id, when available;
- result_timestamp_utc;
- account_scope;
- source_class;
- source_sequence.

Unavailable broker fields must be represented as null with an explicit unavailable-field note, not replaced with an inferred value.

## 7. Position snapshot schema

Two separate top-level collections are required:

- position_snapshots_before;
- position_snapshots_after.

Every snapshot record must support:

- snapshot_id;
- request_correlation_id, where the snapshot is related to a request;
- position_ticket;
- symbol;
- type;
- volume;
- price_open;
- sl;
- tp;
- open_time_utc;
- magic;
- comment;
- account_scope;
- snapshot_timestamp_utc;
- source_sequence;
- source_class.

The before and after snapshots must preserve all pre-existing same-symbol positions. A snapshot containing only the newly suspected position is incomplete for testing the legacy maximum-position-ticket heuristic.

The protocol must not assume that the maximum numeric position ticket in the after snapshot was created by the request.

## 8. History-order schema

Every related historical order must be a separate record containing:

- order_ticket;
- position_id, when available;
- symbol;
- type;
- state;
- volume_initial;
- volume_current;
- time_setup_utc;
- time_done_utc;
- request_correlation_id, when available;
- application_order_id, when available;
- magic;
- comment;
- account_scope;
- source_sequence;
- retrieval_batch_id;
- source_class.

The absence of position_id or request correlation must remain explicit. It must not be filled from a legacy trades.ticket value.

## 9. History-deal schema

Every related deal must be a separate record in history_deals. A single aggregate deal object is insufficient.

Each deal record must contain:

- deal_ticket;
- order_ticket;
- position_id;
- entry_exit;
- symbol;
- volume;
- price;
- profit;
- commission;
- swap;
- fee;
- timestamp_utc;
- magic;
- comment;
- account_scope;
- source_sequence;
- retrieval_batch_id;
- source_class;
- source_event_id, when available.

deal_ticket and position_id must remain distinct. A deal record may reference a position, but position_id is not a substitute for deal_ticket.

Multiple entry deals for one order and multiple exit deals for one position must remain separate records even when their numeric values or payloads appear related.

## 10. Repeated history retrieval schema

Every repeated retrieval must be represented by a retrieval_batches record containing:

- capture_id;
- query_id;
- query_type;
- account_scope;
- query_start_utc;
- query_end_utc;
- retrieval_timestamp_utc;
- retrieval_sequence;
- pagination_or_cursor;
- returned_event_ids_in_returned_order;
- returned_event_timestamps_in_returned_order;
- event_payload_digests;
- complete_response_digest;
- overlap_with_previous_retrieval;
- already_observed_flags;
- source_class;
- completeness.

The returned order must be preserved exactly as observed. Do not sort the list during collection or sanitization.

Repeated retrievals of the same query window must retain the retrieval sequence and response digest. A repeated application record is not automatically a replayed broker event.

## 11. Collision-analysis requirements

collision_analysis must preserve relation tokens for:

- the same order number across account/server scopes;
- the same position number across account/server scopes;
- the same deal number across account/server scopes;
- the same numeric value across order, position, and deal types;
- values reused across separate lifecycle intervals.

Each relation entry must identify:

- relation_id;
- identity_type;
- account_scope;
- lifecycle_interval;
- numeric_relation_token;
- observed_equal_to;
- observed_not_equal_to;
- source_event_refs;
- confidence.

Sanitization may replace raw identifiers with stable tokens such as SANITIZED_ORDER_001 or SANITIZED_NUMERIC_RELATION_001. It must not collapse distinct values or erase equality relationships.

A finite dataset can prove a collision occurred within its declared scope. It cannot prove global uniqueness from the absence of collisions.

## 12. Required lifecycle case matrix

The case_matrix must include each case exactly once with one of these statuses:

- CAPTURED — complete required evidence exists for the declared case.
- NOT_OBSERVED — the case was searched for in the declared scope but was not found.
- UNAVAILABLE — the required source/evidence was not available or completeness could not be established.

NOT_OBSERVED is not IMPOSSIBLE. UNAVAILABLE is not a negative broker fact.

Required cases:

1. one order → one deal → one position;
2. one order → multiple entry deals;
3. partial fill;
4. partial close;
5. full close;
6. close → reopen on the same symbol;
7. multiple simultaneous same-symbol positions;
8. at least two account/server scopes;
9. repeated history retrieval;
10. duplicate/replayed broker event.

Each case must reference the relevant request, result, snapshot, order, deal, and retrieval records. A CAPTURED case with missing references is invalid.

## 13. Activation evidence

activation_evidence must classify newer modules without starting them.

For each module or process record:

- module;
- expected role;
- activation_status;
- launcher_or_process_source;
- startup_reference;
- runtime_evidence_reference;
- source_class;
- confidence;
- notes.

Allowed activation statuses are:

- ACTIVE;
- INACTIVE;
- TEST_ONLY;
- DIAGNOSTIC;
- UNKNOWN.

Source-file presence and importability are not runtime activation proof. Do not classify a module ACTIVE without launcher, process, deployment, or startup evidence.

## 14. Acceptance criteria

The evidence package can advance the identity gate only when all of the following are satisfied:

1. The manifest identifies the source, scope, time window, completeness, and sanitization.
2. Account scope and account mode are explicitly evidenced for every account in scope.
3. Requests, broker results, before/after positions, history orders, and every related deal are correlated.
4. All deal records are independent, with order and position references kept distinct.
5. The required lifecycle cases are marked CAPTURED, NOT_OBSERVED, or UNAVAILABLE with supporting references.
6. Repeated history retrievals preserve returned order, timestamps, query overlap, pagination, and response digests.
7. Collision relationships across accounts and identity types are preserved.
8. No absence in a finite sample is described as global uniqueness or impossibility.
9. Maximum-position-ticket selection is either demonstrated for each captured request or remains explicitly UNKNOWN and is rejected as a canonical mapping.
10. Newer module activation is supported by runtime/deployment evidence or remains UNKNOWN.
11. No current UNKNOWN is promoted from configuration, synthetic behavior, or an application-generated hash.
12. No credentials, secrets, raw account identifiers, or production runtime state are included.

Passing these criteria means the evidence is sufficient for a subsequent identity-design decision. It does not authorize production implementation.

## 15. Evidence submission rules

Future broker evidence must be:

- sanitized before repository insertion;
- explicitly marked as historical, recorded, or synthetic;
- accompanied by provenance;
- relation-preserving;
- free of credentials and secrets;
- immutable after collection;
- stored separately from production runtime artifacts;
- accompanied by a completeness declaration;
- reviewed without modifying the original capture;
- kept distinct from the legacy trades.ticket value.

Do not create or modify an actual broker evidence dataset during Phase 17.

