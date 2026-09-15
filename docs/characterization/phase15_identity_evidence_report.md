# Phase 15 — Identity Evidence Report

## 1. Executive summary

Phase 15 inspected the repository for evidence that could resolve the Phase 13 identity blockers without connecting to MT5, a broker, a network service, or a production database.

The repository contains useful application and characterization evidence, but it does not contain the authoritative broker facts or complete execution records required to resolve the blockers.

- ai-service/trade_evidence.jsonl contains two repeated application evidence records for one account and one recorded order/position/deal triple. The records are labeled raw/failed evidence and do not include server, environment, event arrays, or a complete MT5 request/history sequence.
- ai-service/oms_ledger.jsonl contains application lifecycle entries, but it does not contain order tickets or deal tickets and its provenance as active production evidence is not established.
- packages/execution/trade_evidence.py and the Phase 12 value objects prove that the application can represent separate identity fields; they do not prove MT5 namespace semantics.
- ai-service/config.json contains application hedge and partial-close policy flags, but no MT5 account margin-mode snapshot. Those flags do not prove netting or hedging mode at the broker.
- Characterization fixtures and edge-case tests are synthetic. They prove application handling of supplied values only and cannot establish broker behavior.
- No authoritative MT5, MetaQuotes, or broker identifier documentation was found in the repository.

The production identity blockers therefore remain unresolved. No identity mapping, reconciliation, migration, or production change is authorized.

## 2. Evidence sources inspected

### Phase artifacts

- docs/characterization/phase12_canonical_identity_account_model.md
- docs/characterization/phase13_production_identity_evidence.md
- docs/characterization/phase14_identity_evidence_plan.md
- tests/characterization/test_phase12_canonical_identity_account_model.py
- tests/characterization/legacy_v3_fixtures.py
- tests/test_mt5_edge_cases.py
- tests/characterization/legacy_v3_baseline.json

### Identity and reconciliation source

- packages/execution/mt5_identity.py
- packages/execution/canonical_execution_identity.py
- packages/execution/mt5_reconciler.py
- packages/execution/trade_evidence.py
- packages/execution/account_context.py
- packages/execution/account_manager.py
- packages/observability/reconciliation_daemon.py
- packages/observability/system_integrity_gate.py

### Existing evidence/configuration artifacts

- ai-service/trade_evidence.jsonl
- ai-service/oms_ledger.jsonl
- research/evidence_objects/evidence_198984e6ee786166.json
- packages/research/research_records.json
- docs/EVIDENCE_COLLECTION_PROTOCOL.md
- docs/STATISTICAL_EVIDENCE.md
- relevant portions of ai-service/config.json

### Activation evidence

- deploy/start_all.bat
- scripts/start.sh
- docker-compose.yml
- packages/observability/watchdog.py
- packages/observability/health_monitor.py
- repository references to reconciliation and account-context modules

No file-backed production database was opened. No MT5 API was initialized. No network or broker service was contacted. No configuration or runtime state was modified.

## 3. Evidence classification

This report separates:

- BROKER FACT — established by authoritative broker/MT5 material or a complete, trusted broker export. No new broker fact was established in this phase.
- APPLICATION FACT — behavior or data shape directly established by repository source or an existing application artifact.
- SYNTHETIC BEHAVIOR — behavior observed using fakes, fixtures, or test values. It does not establish live broker behavior.
- INFERENCE — a plausible interpretation that must not be encoded as a production identity rule.

Confidence uses:

- PROVEN
- STRONGLY INDICATED
- INFERRED
- UNKNOWN

Files with names such as evidence or ledger are not automatically authoritative. Provenance, completeness, source fields, and activation must be established before they can prove broker behavior.

## 4. Account-scope findings

### Evidence found

ai-service/trade_evidence.jsonl contains one account/login pair and one set of order, position, and deal fields. It does not include server, environment, broker namespace, account mode, or a second account. The two records repeat the same signal and identity values with different creation timestamps and the same evidence hash. This proves that the application evidence ledger contains repeated records; it does not prove that MT5 replayed a history event.

packages/execution/trade_evidence.py defines account_id and MT5_login, but no server or environment field. packages/execution/account_context.py defines account ID, account name, environment, and broker server for newer application code. These are application models, not captured broker account snapshots.

ai-service/config.json contains account/server configurations and flags such as hedge_mode_enabled and enable_partial_close. These are application configuration choices. They do not report MT5 margin_mode or prove the server's actual netting/hedging mode.

### Finding

The strongest observed operational account scope is login/account number plus server. Account name and environment remain application labels. The legacy TradeLogger does not receive complete account scope on entry, and the legacy exit remains ticket-only. No repository artifact establishes account-scoped broker identifier uniqueness or proves that two configured accounts cannot share a numeric identifier.

Classification: APPLICATION FACT for field availability; UNKNOWN for authoritative broker namespace and collision behavior.

## 5. Order identity findings

packages/execution/mt5_identity.py documents mt5.order_send().order as an order identity and keeps it separate from position and deal fields. The Phase 12 value model likewise defines a typed OrderIdentity scoped by AccountScope.

The evidence ledger contains one order_ticket field, but it does not contain the original trade request, result.order payload, retcode, server, or a before/after position snapshot. Phase 13 source findings still prove that the legacy broker path may put result.order into trades.ticket when no position is found.

No authoritative MT5/broker documentation exists in the repository to establish whether numeric order tickets are globally unique, account-unique, account/server-unique, or scoped differently.

Result: MT5 order-ticket namespace is UNKNOWN. Repository evidence is insufficient. A finite single-account record cannot establish global or account-wide uniqueness.

## 6. Position identity findings

The repository uses positions_get()[].ticket as a position reference in newer code, and deal.position_id as a reference to that position. packages/execution/mt5_reconciler.py queries history by a supplied position ticket and filters deals by position_id.

Synthetic edge-case tests use distinct position values for two positions and for a reopen. Those assertions establish only the intended behavior of the test values. They are not broker namespace evidence.

The existing evidence ledger has one position-ticket field, but no complete position snapshot, account/server scope, position mode, or lifecycle sequence. The OMS ledger contains position labels in application state transitions, but not a broker position record tied to order/deal history.

Result: MT5 position-ticket namespace is UNKNOWN. The repository proves the application treats a position ticket as a distinct concept in newer code, not the uniqueness scope of the underlying broker value.

## 7. Deal identity findings

deal.ticket is represented separately in mt5_identity.py, canonical_execution_identity.py, and trade_evidence.py. The repository also proves that deal.position_id is a position reference and must not be treated as the deal identity.

The existing evidence ledger contains one aggregate deal_ticket field, but no entry/exit deal arrays, no event type sequence, no source event ID, and no complete history retrieval metadata. The legacy persistence path still does not store deal tickets separately.

No authoritative broker documentation or multi-account history export is present to establish deal-ticket uniqueness scope or replay guarantees.

Result: MT5 deal-ticket namespace is UNKNOWN. The identity distinction is an APPLICATION FACT; broker uniqueness is not proven.

## 8. Multi-fill / partial-fill findings

Existing evidence includes:

- tests/test_mt5_edge_cases.py contains a synthetic partial-fill volume mismatch and a synthetic partial-close deal.
- tests/characterization/legacy_v3_fixtures.py provides a fake MT5 object, but it returns no historical deals by default and contains no multi-deal recorded sequence.
- packages/execution/mt5_identity.py stores only one entry deal in TradeIdentity; repeated entry deals overwrite that field.
- packages/execution/mt5_reconciler.py stores one entry_deal; repeated entry deals overwrite it.
- The legacy entry path writes one trade row and does not store each deal.
- ai-service/trade_evidence.jsonl contains one aggregate deal field, not a per-deal execution array.

The repository proves that synthetic partial-fill scenarios are contemplated and that current legacy/newer structures do not provide complete multi-entry deal persistence. It does not contain a real or complete recorded order with multiple entry deals.

Result: One-order/multiple-deal behavior and production partial-fill behavior are UNKNOWN. The synthetic tests are not broker evidence.

## 9. Partial-close findings

The application configuration contains partial-close flags, and synthetic tests describe a position with one partial exit. mt5_reconciler.py appends exit observations to an in-memory partial_deals list, but its single exit_deal field is overwritten by later exit observations. The legacy logger has one exit state per ticket-matched row and no deal-level event ledger.

No existing artifact contains one position with two or more independently captured exit deals, quantities, remaining-volume snapshots, and source event identities. The OMS ledger's POSITION_CLOSED state is an application state transition and does not prove partial-close broker history.

Result: Partial-close behavior is UNKNOWN as a production broker fact. The inability of the legacy schema to preserve independent exit deals is an APPLICATION FACT.

## 10. Close-and-reopen findings

tests/test_mt5_edge_cases.py uses two different synthetic position values for a close/reopen scenario. This proves only that the test distinguishes two values. It does not provide an observed old-position close followed by a new order/position sequence.

The OMS ledger contains application-level open/close transitions, including test-like order IDs, but no paired order/deal identity chain sufficient to prove close-and-reopen lineage. No historical execution export was found.

Result: Close-and-reopen lineage is UNKNOWN.

## 11. History ordering and replay findings

No recorded MT5 history retrieval batches, pagination metadata, source list ordering, overlapping query windows, or repeated snapshots were found.

The two trade_evidence.jsonl records repeat an application evidence record, but their different created_at values and same evidence hash do not identify a broker event replay. The repeated OMS test/application records likewise do not contain MT5 history event IDs or retrieval batches.

The source code has no established idempotent history-ingestion protocol and does not prove that the order returned by history_deals_get is a stable chronological order.

Result: History ordering is UNKNOWN. Duplicate/replay behavior is UNKNOWN as a broker fact; repeated application records are PROVEN only as an artifact observation.

## 12. Idempotency findings

The repository contains candidate identifiers—order ticket, position ticket, deal ticket, and application order_id—but no proven source event ID contract used by the legacy persistence path. trade_evidence.py computes an evidence hash from selected application fields, not from a broker event identity, and its ledger writer appends records.

The repeated SIG_163 evidence rows show that duplicate application records can exist. They do not establish whether the underlying broker event was duplicated, whether the record was intentionally re-emitted, or whether the hash is an idempotency key.

Result: No stable broker event idempotency key is proven. Idempotency requirements remain UNKNOWN and must be treated as an explicit future reconciliation requirement.

## 13. Maximum-position-ticket correlation findings

The legacy source path is proven to select the maximum position ticket visible for a symbol after a successful order result, falling back to result.order when no position is present. This is an APPLICATION FACT.

No repository evidence contains all of the following in one correlated sequence:

- request correlation ID;
- order submission result;
- positions before submission;
- positions after submission;
- pre-existing same-symbol positions;
- selected maximum ticket;
- eventual entry deal and position relationship.

The evidence ledger's single order/position/deal triple lacks this sequence and does not prove that the selected position came from the submitted order.

Result: Maximum-position-ticket selection is not proven safe as a canonical mapping. UNKNOWN.

## 14. Netting vs hedging findings

ai-service/config.json contains per-account application flags such as hedge_mode_enabled, hedge thresholds, and partial-close configuration. These values express application policy or feature configuration. They are not an MT5 account margin_mode or a broker account-mode snapshot.

packages/execution/account_context.py defines environments and servers but does not capture margin mode. The fake MT5 account object in characterization fixtures has login and margin-free values but no account-mode evidence.

No sanitized account_info snapshot, MT5 margin-mode field, or authoritative broker account-mode document is present.

Result: Active account mode is UNKNOWN. Neither netting nor hedging is proven for the deployed accounts.

## 15. New reconciliation/account-context activation findings

### Launchers

deploy/start_all.bat starts the legacy auto_trader_exness.py, backend, frontend, watchdog, health monitor, and V3 dashboard API. It does not start packages/observability/reconciliation_daemon.py, packages/execution/account_manager.py, or a canonical identity service.

scripts/start.sh starts ai_service.py, the backend, and frontend. It does not start the newer identity or reconciliation modules.

docker-compose.yml starts the V3 API, backend, and frontend. It does not activate the newer identity/account/reconciliation workers.

The watchdog's configured trading restart command also points to the legacy auto_trader_exness.py.

### Indirect references

system_integrity_gate.py imports ReconciliationDaemon as an importability health check, but the inspected launchers do not start the integrity gate as a dedicated production process. health_monitor.py performs its own direct MT5 and database checks; it does not establish that the newer reconciliation daemon is running.

account_context.py, account_manager.py, and mt5_reconciler.py are used by tests, health/integrity utilities, or newer code paths, but source presence and test imports are not runtime activation evidence.

Result: New reconciliation/account-context production activation is not proven. Available launcher evidence strongly indicates that the legacy trading daemon remains the primary configured trading path, while newer modules are diagnostic, experimental, or otherwise unverified. Exact runtime status remains UNKNOWN without process/startup evidence.

## 16. Phase 14 minimum-dataset coverage table

| Phase 14 Requirement | Evidence Found | Source Class | Scope | Result | Remaining Gap |
|---|---|---|---|---|---|
| Order-ticket namespace and uniqueness | Typed application fields and one recorded triple; no broker namespace documentation. | APPLICATION FACT / RECORDED APPLICATION ARTIFACT | One account, one record | BLOCKED | Authoritative namespace scope or complete scoped historical evidence. |
| Position-ticket namespace and uniqueness | Position identity value objects, synthetic values, one recorded position field. | APPLICATION FACT / SYNTHETIC BEHAVIOR | One account, no lifecycle export | BLOCKED | Account/server-scoped broker evidence and lifecycle coverage. |
| Deal-ticket namespace and uniqueness | Separate deal fields in newer models and one aggregate evidence field. | APPLICATION FACT | One recorded deal value | BLOCKED | Authoritative deal namespace or scoped history export. |
| Cross-account numeric collisions | Multiple account names/config contexts exist, but no comparable order/position/deal records across accounts. | APPLICATION CONFIGURATION | No execution comparison | BLOCKED | Two or more account-scoped execution datasets preserving equality relations. |
| Active account mode | Hedge/partial-close policy flags in config; no MT5 margin mode. | APPLICATION CONFIGURATION | Configured accounts, not broker state | BLOCKED | Sanitized account-info/margin-mode evidence. |
| One order/multiple entry deals | No multi-deal export; single-deal evidence field only. | APPLICATION FACT / ABSENCE | One aggregate record | BLOCKED | Correlated order/result/history deal sequence. |
| Partial-fill behavior | Synthetic volume mismatch test. | SYNTHETIC BEHAVIOR | Isolated fake values | BLOCKED | Trusted recorded multi-deal quantity sequence. |
| Partial-close behavior | Synthetic one-exit test, config flags, in-memory reconciler list. | SYNTHETIC BEHAVIOR / APPLICATION CONFIGURATION | No real multi-exit sequence | BLOCKED | Position snapshots plus multiple exit deals. |
| Close-and-reopen lineage | Synthetic distinct tickets and application OMS states. | SYNTHETIC BEHAVIOR / APPLICATION ARTIFACT | No broker lineage | BLOCKED | Ordered old-close/new-open execution export. |
| History ordering | No retrieval batches, pagination, or source ordering evidence. | NONE | Not available | BLOCKED | Repeated retrieval/export with sequence metadata. |
| Duplicate/replay observations | Repeated application evidence rows and OMS entries. | RECORDED APPLICATION ARTIFACT | Application ledger only | BLOCKED | Stable broker source event IDs across repeated observations. |
| Idempotency key | Evidence hash and application order IDs exist, but no source-event contract. | APPLICATION FACT | Not proven broker identity | BLOCKED | Scoped stable source event identity and replay examples. |
| Maximum-ticket correlation | Legacy branch is characterized; no correlated before/after position evidence. | APPLICATION FACT | Code path only | BLOCKED | Request/result/position snapshot sequence. |
| Newer module activation | Launchers omit newer workers; health gate only imports reconciliation daemon. | APPLICATION FACT | Launcher/source inspection | BLOCKED | Verified process/startup evidence or explicit deployment record. |

## 17. PROVEN / STRONGLY INDICATED / INFERRED / UNKNOWN table

| Claim | Classification | Result | Evidence basis |
|---|---|---|---|
| Legacy broker path can place a position ticket or result.order into trades.ticket. | PROVEN | Yes | broker_exness.py and Phase 13 characterization. |
| deal.position_id is used as the legacy exit lookup value. | PROVEN | Yes | auto_trader_exness.py path and Phase 13 report. |
| Legacy trades.ticket is opaque and non-unique in the local schema. | PROVEN | Yes | Legacy schema and isolated characterization. |
| Newer application models distinguish order, position, and deal fields. | PROVEN | Yes | mt5_identity.py, canonical_execution_identity.py, trade_evidence.py. |
| Repository has one repeated application evidence record with separate order/position/deal fields. | PROVEN | Yes | Two trade_evidence.jsonl rows; same event content/hash, different creation times. |
| Application configuration expresses hedge/partial-close policy. | PROVEN | Yes | ai-service/config.json. |
| Newer reconciliation/account-context modules are not started by inspected launchers. | STRONGLY INDICATED | Yes, from available launcher evidence | Launchers start legacy daemon/watchdog; newer modules appear in health/test references. |
| Repeated evidence rows represent a broker replay. | INFERRED | No | No source event ID or retrieval batch. |
| Configured hedge mode means MT5 account mode is hedging. | INFERRED | No | Application flag is not broker margin-mode evidence. |
| One order produces one position and one deal. | INFERRED | No | One aggregate record cannot prove lifecycle cardinality. |
| MT5 order-ticket namespace is globally unique. | UNKNOWN | No | No authoritative documentation or complete scoped export. |
| MT5 position-ticket namespace is globally unique. | UNKNOWN | No | No broker namespace evidence. |
| MT5 deal-ticket namespace is globally unique. | UNKNOWN | No | No broker namespace evidence. |
| MT5 identifiers are unique within account/server scope. | UNKNOWN | No | One account record cannot establish this. |
| Active accounts are netting or hedging. | UNKNOWN | No | No margin-mode snapshot. |
| One order can produce multiple deals in the deployed path. | UNKNOWN | No | No complete recorded multi-deal sequence. |
| Partial fills occur and are fully represented. | UNKNOWN | No | Synthetic tests only; legacy schema is aggregate. |
| Partial closes occur and are fully represented. | UNKNOWN | No | Config/test intent is not broker evidence. |
| Close-and-reopen lineage is captured. | UNKNOWN | No | No complete old/new execution sequence. |
| Broker history ordering is stable and chronological. | UNKNOWN | No | No retrieval-order evidence. |
| Duplicate/replayed broker history observations are distinguishable. | UNKNOWN | No | No source event/replay evidence. |
| Stable idempotency key is available. | UNKNOWN | No | Deal ticket is a candidate, not a proven scoped event key. |
| Maximum-position-ticket selection is correlated with the submitted order. | UNKNOWN | No | No request/result/position correlation capture. |
| Newer reconciliation/account-context code is production-active. | UNKNOWN | No | Source presence/importability is not activation proof. |
| Production identity mapping is safe to design now. | UNKNOWN | No | Critical broker and lifecycle evidence remains absent. |

## 18. Remaining blockers

1. No authoritative identifier namespace/uniqueness documentation is present.
2. No complete sanitized MT5 history export with account/server scope exists.
3. No account-mode margin snapshot exists.
4. No correlated request/result/position-before-and-after capture exists to validate maximum-ticket selection.
5. No multi-entry-deal or multi-exit-deal execution sequence exists.
6. No close-and-reopen sequence exists with typed identities and ordering.
7. No history retrieval/pagination/replay evidence exists.
8. No stable source event/idempotency contract is proven.
9. No verified process evidence establishes whether newer reconciliation and account-context code is active.
10. Existing application evidence records are incomplete, repeated, and not independently proven to be sanitized authoritative broker exports.

## 19. Recommendation for Phase 16

Do not begin production identity mapping or reconciliation implementation.

Phase 16 should be an evidence-acquisition/validation phase only, using the Phase 14 template and minimum dataset. The safest source is an approved, sanitized, read-only historical export or a complete recorded response bundle from a controlled environment. It must include account/server scope, request and result correlation, position snapshots, all entry/exit deals, event timestamps, retrieval sequence, and completeness metadata.

If no such evidence can be obtained without live-state access, the project should remain blocked rather than infer broker semantics from configuration, synthetic fixtures, or a single aggregate evidence record.

No future phase may reinterpret legacy trades.ticket as an order, position, or deal identity merely because newer artifacts contain separately named fields.

## 20. Final phase gate

The Phase 14 evidence plan is complete as a plan, but its minimum evidence dataset is not present in the repository. Critical identity behavior remains UNKNOWN.

PHASE 15 GATE: BLOCKED — INSUFFICIENT EVIDENCE

