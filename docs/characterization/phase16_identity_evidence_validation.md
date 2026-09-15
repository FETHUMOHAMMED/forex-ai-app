# Phase 16 — MT5 Identity Evidence Validation

## 1. Executive summary

Phase 16 performed an offline repository-only validation against the Phase 14 minimum evidence plan.

The repository does not contain a complete broker evidence dataset. It contains:

- application source that proves how identifiers are assigned and consumed;
- synthetic MT5 fixtures and edge-case tests;
- one repeated application evidence record in ai-service/trade_evidence.jsonl with separate order, position, and deal fields;
- application lifecycle entries in ai-service/oms_ledger.jsonl;
- application configuration flags for hedge and partial-close behavior;
- launcher evidence showing the legacy trading daemon is the configured path.

None of those artifacts proves the broker-level facts still required. The recorded evidence has one account, no server/environment scope, no account-mode snapshot, no request/result correlation, no before/after position snapshots, no history-order records, and no per-deal lifecycle arrays. Its records are labeled raw/failed and are repeated without a broker source event identity.

The required evidence for order, position, and deal namespaces, account mode, fills, closes, history ordering, replay, idempotency, and maximum-ticket correlation is therefore absent or incomplete.

No production identity mapping is safe to implement.

## 2. Scope and safety boundary

This phase was limited to static repository inspection and reading existing repository artifacts. It did not:

- initialize MT5;
- call a broker or network service;
- submit, modify, close, or inspect live orders or positions;
- open trades.db or another file-backed production database;
- execute production runtime code;
- modify production code, tests, schemas, configuration, caches, launchers, or evidence files.

The only authorized write is this report.

## 3. Evidence sources inspected

### Phase documents and baseline

- docs/characterization/phase13_production_identity_evidence.md
- docs/characterization/phase14_identity_evidence_plan.md
- docs/characterization/phase15_identity_evidence_report.md
- docs/characterization/phase12_canonical_identity_account_model.md
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
- packages/observability/health_monitor.py
- packages/observability/system_integrity_gate.py

### Existing recorded/configuration artifacts

- ai-service/trade_evidence.jsonl
- ai-service/oms_ledger.jsonl
- research/evidence_objects/evidence_198984e6ee786166.json
- packages/research/research_records.json
- relevant fields in ai-service/config.json
- docs/EVIDENCE_COLLECTION_PROTOCOL.md
- docs/STATISTICAL_EVIDENCE.md

### Activation evidence

- deploy/start_all.bat
- scripts/start.sh
- docker-compose.yml
- packages/observability/watchdog.py
- ai-service/watchdog.py
- static references to reconciliation, account-context, and account-manager modules

No authoritative MT5, MetaQuotes, or broker identifier documentation was found in the repository.

## 4. Evidence provenance assessment

### ai-service/trade_evidence.jsonl

The file contains two records for the same application signal and the same account/login and order/position/deal values. The records have different application creation timestamps but the same evidence hash. They include aggregate planned/actual fields and decision labels, but no server, environment, account-mode field, raw broker request, raw broker result, position snapshots, history orders, deal arrays, retrieval metadata, or source event ID.

The records are classified as a RECORDED APPLICATION ARTIFACT, not a BROKER FACT. Their own fields label the execution as raw/exception/failure. The repeated rows prove repeated application evidence records, not broker replay.

### ai-service/oms_ledger.jsonl

The file contains application state transitions such as order creation, submission, fill, position open, close, reconciliation, and settlement. It includes application order IDs, account labels, broker labels, and position labels, but not MT5 order tickets, deal tickets, request results, history retrieval metadata, or source event IDs. Some entries are explicitly test-like.

It is a RECORDED APPLICATION ARTIFACT. It cannot prove that the represented lifecycle occurred in MT5 or that the application module producing it was active in the verified legacy runtime.

### Synthetic fixtures and tests

The fake MT5 fixture, edge-case tests, and identity tests demonstrate how application code handles values supplied by tests. They are SYNTHETIC BEHAVIOR. They cannot prove identifier uniqueness, broker account mode, actual fill cardinality, history ordering, or live replay behavior.

### Configuration

ai-service/config.json contains account/server settings and flags including hedge-mode and partial-close policy. This is an APPLICATION FACT. It is not authoritative MT5 account-mode evidence and cannot establish netting or hedging.

### Research artifacts

research/evidence_objects/evidence_198984e6ee786166.json and packages/research/research_records.json contain research/backtest evidence. They do not contain a complete MT5 order/deal/position export and are not relevant broker lifecycle evidence.

## 5. Account-scope findings

The repository provides application account fields in different places:

- legacy account configuration supplies login/account number and server;
- application labels include account name and environment;
- newer AccountContext includes account ID, name, environment, and broker server;
- TradeEvidenceRecord includes account_id and MT5_login but not server or environment;
- the recorded evidence file contains only one account scope;
- no trusted account_info snapshot contains margin mode, currency, leverage, and capture provenance.

### Validation result

| Requirement | Evidence found | Source | Source class | Scope | Confidence | Result | Remaining gap |
|---|---|---|---|---|---|---|---|
| account/login | One account/login in trade evidence and application models | ai-service/trade_evidence.jsonl; trade_evidence.py | RECORDED APPLICATION ARTIFACT | One account | PROVEN | Present as application evidence | Trusted broker snapshot and cross-account comparison |
| broker/server | Server exists in configuration and AccountContext | ai-service/config.json; account_context.py | APPLICATION FACT | Configuration/model only | PROVEN | Present as application context | Broker-sourced server scope on each execution record |
| environment | Environment exists in AccountContext/configuration | account_context.py; ai-service/config.json | APPLICATION FACT | Application context | PROVEN | Present as application label | Trusted account snapshot and per-event propagation |
| account mode/margin mode | No MT5 margin-mode snapshot | fixtures/configuration | UNKNOWN | No broker snapshot | UNKNOWN | BLOCKED | Authoritative account-mode evidence |
| currency | No trusted execution/account snapshot | repository search | UNKNOWN | None | UNKNOWN | BLOCKED | Account snapshot field |
| leverage | No trusted execution/account snapshot | repository search | UNKNOWN | None | UNKNOWN | BLOCKED | Account snapshot field |
| account snapshot timestamp/provenance | Application timestamps exist, but no broker snapshot provenance | trade_evidence.jsonl | RECORDED APPLICATION ARTIFACT | One application record | UNKNOWN | BLOCKED | Source, capture time, completeness, and account snapshot |

## 6. Order identity findings

The repository proves that newer code names result.order as an order ticket and keeps it distinct from position and deal values. The legacy broker path may place result.order into the opaque trades.ticket field when no position is visible.

The recorded evidence has one aggregate order_ticket field but no raw result object, request correlation, result request_id, order state, history order, or account/server scope.

| Requirement | Evidence found | Source | Source class | Scope | Confidence | Result | Remaining gap |
|---|---|---|---|---|---|---|---|
| request correlation ID | Not present in recorded evidence | trade_evidence.jsonl | UNKNOWN | None | UNKNOWN | BLOCKED | Per-request correlation |
| application order ID | Present in OMS records, not correlated to MT5 result | oms_ledger.jsonl | RECORDED APPLICATION ARTIFACT | Application lifecycle only | PROVEN | Application ID exists | Mapping to broker order/result |
| order ticket | One aggregate order_ticket field | trade_evidence.jsonl; trade_evidence.py | RECORDED APPLICATION ARTIFACT | One account/record | PROVEN | Field exists | Raw broker source and namespace scope |
| requested volume/order type/price/SL/TP | Partial planned fields exist; no complete request record | trade_evidence.jsonl and baseline | RECORDED APPLICATION ARTIFACT | One aggregate record | PROVEN | Incomplete | Complete request with account/server and correlation |
| broker result fields | No complete retcode/order/deal/volume/price/request_id result | repository evidence | UNKNOWN | None | UNKNOWN | BLOCKED | Raw result capture |
| order namespace uniqueness | No authoritative documentation or scoped export | repository search | UNKNOWN | None | UNKNOWN | BLOCKED | Broker namespace evidence |

## 7. Position identity findings

The repository proves that positions_get()[].ticket is treated as a position identity in newer code and that deal.position_id is a position reference. It does not prove the underlying numeric namespace.

The recorded evidence has one position_ticket value but no before/after position snapshots, position type, volume lifecycle, magic/comment, account/server scope, or relation to a specific request.

| Requirement | Evidence found | Source | Source class | Scope | Confidence | Result | Remaining gap |
|---|---|---|---|---|---|---|---|
| position ticket | One aggregate position_ticket field | trade_evidence.jsonl | RECORDED APPLICATION ARTIFACT | One record | PROVEN | Field exists | Broker-sourced snapshot and typed lineage |
| position snapshot before request | None | repository search | UNKNOWN | None | UNKNOWN | BLOCKED | Complete before snapshot |
| position snapshot after request | None | repository search | UNKNOWN | None | UNKNOWN | BLOCKED | Complete after snapshot |
| position type/volume/open price | Not present as a complete position snapshot | source/evidence artifacts | UNKNOWN | None | UNKNOWN | BLOCKED | Position snapshot fields |
| position namespace uniqueness | Not established | repository source/tests | UNKNOWN | None | UNKNOWN | BLOCKED | Account/server-scoped broker evidence |

## 8. Deal identity findings

The identity modules keep deal.ticket distinct from order and position identities. The repository also proves that deal.position_id is a position reference, not a deal identity.

The recorded evidence contains one aggregate deal_ticket field and no entry/exit deal array. No history-deal export, source event ID, repeated retrieval, or per-deal quantity/timestamp sequence exists.

| Requirement | Evidence found | Source | Source class | Scope | Confidence | Result | Remaining gap |
|---|---|---|---|---|---|---|---|
| deal ticket | One aggregate deal_ticket field | trade_evidence.jsonl; trade_evidence.py | RECORDED APPLICATION ARTIFACT | One record | PROVEN | Field exists | Broker source, role, position_id, and namespace |
| order ticket on each deal | None in per-deal records | repository evidence | UNKNOWN | None | UNKNOWN | BLOCKED | Per-deal order reference |
| position_id on each deal | None in recorded evidence array | repository evidence | UNKNOWN | None | UNKNOWN | BLOCKED | Per-deal position reference |
| entry/exit role | Application decision labels exist, but no deal entry/exit fields | trade_evidence.jsonl | RECORDED APPLICATION ARTIFACT | One aggregate record | UNKNOWN | BLOCKED | Per-deal entry/exit field |
| deal volume/price/PnL/commission/swap/fee/time | Not present as a complete per-deal set | trade_evidence.py has optional model fields only | APPLICATION FACT | Model only | PROVEN | Model capability, not data | Complete history-deal records |
| deal namespace uniqueness | Not established | repository source/tests | UNKNOWN | None | UNKNOWN | BLOCKED | Authoritative or scoped broker evidence |

## 9. Multi-deal findings

The repository has no complete broker-recorded multi-deal sequence.

- TradeIdentity has one entry-deal slot; later entry observations overwrite it.
- MT5PositionLineage has one entry_deal and an in-memory partial_deals list for exits.
- Legacy TradeLogger stores one aggregate row per accepted entry.
- TradeEvidenceRecord has one deal_ticket field.
- Synthetic tests mention volume mismatch but do not contain multiple broker deals.

Result: one order to multiple entry deals is UNKNOWN. The application data model is not evidence that this occurred or did not occur.

## 10. Partial-fill findings

The only partial-fill evidence is synthetic volume comparison in tests and application configuration/policy. No recorded order contains requested volume, multiple execution volumes, cumulative volume, remaining volume, and all related deals.

Result: production partial-fill behavior is UNKNOWN. A trusted sequence with all entry deals is required.

## 11. Partial-close findings

Configuration includes partial-close flags and synthetic tests contain a one-exit example. No existing artifact contains one position with two or more exit deals, remaining-volume snapshots, exit quantities, and source event IDs.

Result: production partial-close behavior is UNKNOWN. The legacy schema's inability to preserve independent exit deals is an APPLICATION FACT, but it does not establish how MT5 generated them.

## 12. Close/reopen findings

Synthetic tests use different values for a close/reopen example. OMS entries show application state transitions, but no correlated old position, close deals, new order, new position, or account/server-scoped sequence is present.

Result: close-and-reopen lineage is UNKNOWN.

## 13. History-ordering findings

No repository artifact records:

- history_deals_get retrieval batches;
- history_orders_get retrieval batches;
- query windows or pagination;
- returned list order;
- source event sequence;
- repeated retrieval timestamps;
- complete event payload hashes.

Source code does not establish that MT5 history results are returned chronologically or deterministically.

Result: history ordering is UNKNOWN.

## 14. Replay/duplicate findings

The two trade_evidence.jsonl rows repeat the same application event content and hash with different creation timestamps. This is evidence of repeated application records only. There is no broker retrieval batch, source event ID, or payload showing that the same MT5 event was replayed.

OMS records also contain repeated test-like application transitions, not broker history replay evidence.

Result: duplicate/replayed broker behavior is UNKNOWN.

## 15. Idempotency findings

| Candidate identity | Evidence status | Classification | Result |
|---|---|---|---|
| order ticket | One aggregate field only | RECORDED APPLICATION ARTIFACT | Not proven as a stable source event key |
| position ticket | One aggregate field and synthetic values | APPLICATION FACT | Not proven as event identity |
| deal ticket | One aggregate field; no repeated source retrieval | RECORDED APPLICATION ARTIFACT | Candidate only, not proven idempotency key |
| application order_id | Present in OMS ledger | RECORDED APPLICATION ARTIFACT | Application lifecycle key, not proven broker event key |
| request_id | No complete result/request record | UNKNOWN | Not available |
| evidence hash | Same hash on repeated application records | RECORDED APPLICATION ARTIFACT | Not an idempotency key without source-event proof |
| source event ID | None found | UNKNOWN | Required for future reconciliation evidence |

No stable idempotency key is proven. A future composite key must not be selected until broker scope and event semantics are established.

## 16. Cross-account findings

The repository contains multiple configured account labels and contexts, but the available execution evidence covers only one account/login. No second account has comparable order, position, and deal records.

There is no evidence showing:

- the same numeric order under two account/server scopes;
- the same numeric position under two account/server scopes;
- the same numeric deal under two account/server scopes;
- one numeric value reused across identity types;
- account/server/environment attached to every execution event.

Result: cross-account collision behavior is UNKNOWN. A single-account dataset cannot establish global uniqueness or account/server uniqueness.

## 17. Netting/hedging findings

Application flags hedge_mode_enabled, hedge_mode_threshold, and partial-close settings are not broker account-mode evidence. The fake account object has login and margin values but no margin_mode. AccountContext has environment/server but no authoritative MT5 mode snapshot.

Result: active account mode is UNKNOWN. Neither netting nor hedging is proven.

## 18. Maximum-ticket correlation findings

The application behavior is proven: after successful submission, the legacy broker path selects the maximum visible position ticket for the symbol, otherwise it returns result.order.

The repository contains none of the complete correlated components required to validate that heuristic:

| Required component | Evidence found | Source class | Result |
|---|---|---|---|
| request correlation ID | None | UNKNOWN | BLOCKED |
| broker result | No complete raw result | UNKNOWN | BLOCKED |
| positions before request | None | UNKNOWN | BLOCKED |
| positions after request | No complete snapshot | UNKNOWN | BLOCKED |
| pre-existing same-symbol positions | No correlated snapshot | UNKNOWN | BLOCKED |
| selected maximum ticket | Source branch only | APPLICATION FACT | Behavior known, safety unknown |
| eventual entry deal | One aggregate evidence field only | RECORDED APPLICATION ARTIFACT | Not correlated |
| resulting position relationship | No complete lineage | UNKNOWN | BLOCKED |

Result: maximum-position-ticket correlation is UNKNOWN and cannot be used as a canonical mapping.

## 19. Newer-module activation findings

### Launcher evidence

- deploy/start_all.bat starts auto_trader_exness.py, backend, frontend, watchdog, health monitor, and V3 dashboard API.
- scripts/start.sh starts ai_service.py, backend, and frontend.
- docker-compose.yml starts the V3 API, backend, and frontend.
- watchdog configurations restart the legacy auto_trader_exness.py.
- No inspected launcher starts account_manager.py, mt5_reconciler.py, reconciliation_daemon.py, or a canonical identity worker.

### Indirect references

system_integrity_gate.py imports ReconciliationDaemon for an importability check. health_monitor.py performs direct checks but does not prove that ReconciliationDaemon is running. Tests and integrity utilities import newer identity/reconciliation modules.

| Module | Repository status | Source class | Confidence | Required conclusion |
|---|---|---|---|---|
| account_context.py | Present and used by newer code/tests | APPLICATION FACT | PROVEN | Runtime activation UNKNOWN |
| account_manager.py | Present; no launcher activation found | APPLICATION FACT | STRONGLY INDICATED | Runtime activation UNKNOWN |
| mt5_reconciler.py | Present; referenced by tests/integrity | APPLICATION FACT | STRONGLY INDICATED | Runtime activation UNKNOWN |
| reconciliation_daemon.py | Present; imported by integrity gate, not launched directly | APPLICATION FACT | STRONGLY INDICATED | Runtime activation UNKNOWN |
| legacy auto_trader_exness.py | Explicitly launched/restarted | APPLICATION FACT | STRONGLY INDICATED | Configured production path |

The correct status for newer identity/reconciliation activation is UNKNOWN, with the legacy path strongly indicated as the configured trading path.

## 20. Phase 14 minimum-dataset coverage table

| Phase 14 Requirement | Evidence Found | Source | Source class | Scope | Confidence | Result | Remaining gap |
|---|---|---|---|---|---|---|---|
| Account scope | One account/login artifact; server only in configuration; no environment/mode snapshot | trade_evidence.jsonl; config; AccountContext | RECORDED APPLICATION ARTIFACT | One account | UNKNOWN | BLOCKED | Trusted account snapshot with broker/server/environment/mode/currency/leverage/time |
| Trade request | Planned fields only; no request correlation or complete raw request | trade_evidence.jsonl; baseline | RECORDED APPLICATION ARTIFACT | One aggregate record | UNKNOWN | BLOCKED | Full request record |
| Broker result | No complete retcode/order/deal/request_id result | repository evidence | UNKNOWN | None | UNKNOWN | BLOCKED | Raw broker result |
| Position before/after | None | repository search | UNKNOWN | None | UNKNOWN | BLOCKED | Two complete snapshots around request |
| History orders | None | repository search | UNKNOWN | None | UNKNOWN | BLOCKED | All related history orders |
| History deals | One aggregate deal field, no per-deal array | trade_evidence.jsonl; trade_evidence.py | RECORDED APPLICATION ARTIFACT | One record | UNKNOWN | BLOCKED | All related deals with order/position references |
| One order/one deal/one position | No complete correlated broker sequence | repository evidence | UNKNOWN | None | UNKNOWN | BLOCKED | Complete lifecycle record |
| One order/multiple deals | None | repository evidence | UNKNOWN | None | UNKNOWN | BLOCKED | Multi-deal sequence |
| Partial fill | Synthetic volume mismatch only | test_mt5_edge_cases.py | SYNTHETIC BEHAVIOR | Test values | PROVEN for test behavior only | BLOCKED | Trusted broker execution sequence |
| Partial close | Synthetic one-exit case and policy flags | tests/configuration | SYNTHETIC BEHAVIOR | Test/config only | PROVEN for application intent | BLOCKED | Multiple exit deals and remaining-volume snapshots |
| Full close | Application/OMS state labels; no complete MT5 deal chain | oms_ledger.jsonl | RECORDED APPLICATION ARTIFACT | Application state | UNKNOWN | BLOCKED | Broker order/deal/position sequence |
| Close/reopen | Synthetic distinct tickets only | test_mt5_edge_cases.py | SYNTHETIC BEHAVIOR | Test values | PROVEN for test distinction only | BLOCKED | Trusted old-close/new-open sequence |
| Same-symbol simultaneous positions | Synthetic values only | test_mt5_edge_cases.py | SYNTHETIC BEHAVIOR | Test values | PROVEN for test distinction only | BLOCKED | Broker snapshots with account mode |
| Multiple accounts | Config/models only; no comparable executions | config; AccountContext | APPLICATION FACT | Configuration only | PROVEN for configuration presence | BLOCKED | At least two account/server execution scopes |
| Repeated history retrieval | None | repository search | UNKNOWN | None | UNKNOWN | BLOCKED | Repeated capture of identical query window |
| Duplicate/replayed events | Repeated app records only | trade_evidence.jsonl; oms_ledger.jsonl | RECORDED APPLICATION ARTIFACT | Application artifacts | UNKNOWN | BLOCKED | Broker source event IDs and replay batches |
| Maximum-ticket correlation | Source heuristic only | broker path/Phase 13 | APPLICATION FACT | Code behavior | PROVEN for behavior; UNKNOWN for safety | BLOCKED | Request/result/before/after/lineage bundle |
| Newer module activation | Launchers omit newer workers; imports exist | launchers/integrity code | APPLICATION FACT | Repository activation evidence | STRONGLY INDICATED | BLOCKED | Process/startup/runtime evidence |

## 21. PROVEN / STRONGLY INDICATED / INFERRED / UNKNOWN table

| Finding | Source class | Confidence | Result |
|---|---|---|---|
| Legacy broker path can store a position ticket or result.order in trades.ticket. | APPLICATION FACT | PROVEN | Established application behavior |
| Exit path uses deal.position_id as the legacy lookup value. | APPLICATION FACT | PROVEN | Established application behavior |
| Newer identity models keep order, position, and deal fields distinct. | APPLICATION FACT | PROVEN | Established model behavior |
| Local legacy ticket values are nullable and non-unique. | APPLICATION FACT | PROVEN | Established schema behavior |
| trade_evidence.jsonl contains two repeated application records. | RECORDED APPLICATION ARTIFACT | PROVEN | Artifact fact only |
| Application config contains hedge and partial-close policy flags. | APPLICATION FACT | PROVEN | Configuration fact only |
| Legacy auto-trader is the explicitly configured launch target. | APPLICATION FACT | STRONGLY INDICATED | Launcher evidence |
| Newer identity/reconciliation modules are not directly launched by inspected launchers. | APPLICATION FACT | STRONGLY INDICATED | Static activation evidence |
| Repeated evidence rows represent a broker replay. | INFERENCE | INFERRED | Not proven |
| Hedge-mode configuration proves broker hedging mode. | INFERENCE | INFERRED | False as an evidence conclusion |
| One order produces one deal and one position. | INFERENCE | INFERRED | Not proven |
| Order-ticket namespace is globally unique. | UNKNOWN | UNKNOWN | Not proven |
| Position-ticket namespace is globally unique. | UNKNOWN | UNKNOWN | Not proven |
| Deal-ticket namespace is globally unique. | UNKNOWN | UNKNOWN | Not proven |
| Identifiers are unique within account/server scope. | UNKNOWN | UNKNOWN | Not proven |
| Active account mode is netting or hedging. | UNKNOWN | UNKNOWN | Not proven |
| One order can produce multiple deals in production. | UNKNOWN | UNKNOWN | Not proven |
| Partial fills occur and are fully represented. | UNKNOWN | UNKNOWN | Not proven |
| Partial closes occur and are fully represented. | UNKNOWN | UNKNOWN | Not proven |
| Close-and-reopen lineage is captured. | UNKNOWN | UNKNOWN | Not proven |
| History ordering is chronological/deterministic. | UNKNOWN | UNKNOWN | Not proven |
| Duplicate/replayed broker events are distinguishable. | UNKNOWN | UNKNOWN | Not proven |
| A stable source idempotency key exists. | UNKNOWN | UNKNOWN | Not proven |
| Maximum-position-ticket selection is safe. | UNKNOWN | UNKNOWN | Not proven |
| Newer reconciliation/account-context code is production-active. | UNKNOWN | UNKNOWN | Not proven |
| Production identity mapping is safe to implement. | UNKNOWN | UNKNOWN | Not proven |

## 22. Remaining blockers

1. No authoritative MT5/broker namespace documentation is present.
2. No trusted account snapshot establishes margin mode, currency, leverage, and provenance.
3. No complete sanitized multi-account execution export exists.
4. No complete request/result/position-before/position-after bundle exists.
5. No history-order export exists.
6. No per-deal entry/exit history export exists.
7. No multi-fill, partial-close, or close/reopen broker sequence exists.
8. No repeated history retrieval capture establishes ordering or replay behavior.
9. No stable source event identity or idempotency contract is proven.
10. No evidence correlates maximum-position-ticket selection to the submitted order.
11. Newer module activation remains unverified from repository evidence alone.

## 23. Exact evidence-acquisition specification

No acquisition was performed in Phase 16. The following is the minimum future bundle required before the identity gate can be reconsidered.

### 23.1 Capture manifest

Each bundle must include:

- capture_id;
- source class;
- collector/tool version;
- source system;
- account/server scope;
- capture start/end time in UTC;
- retrieval windows and pagination details;
- completeness statement;
- sanitization method;
- proof that credentials and secrets were removed;
- whether records are historical export, recorded response, or synthetic replay.

### 23.2 Account snapshot

For every account in the bundle capture:

- broker;
- login/account alias;
- server alias;
- environment;
- account mode/margin mode;
- currency;
- leverage;
- snapshot timestamp;
- source/provenance;
- any account-level identifier required to interpret ticket scope.

### 23.3 Correlated execution record

For every selected lifecycle case capture:

#### Request

- request correlation ID;
- application order ID;
- account scope;
- symbol;
- side;
- requested volume;
- order type;
- request price;
- requested SL/TP;
- magic/comment;
- request timestamp.

#### Broker result

- retcode;
- result.order;
- result.deal;
- result.volume;
- result.price;
- bid/ask;
- comment;
- request_id if available;
- result timestamp;
- complete request/response relation.

#### Position snapshots

Capture the complete positions list for the symbol before and after the request, including:

- position ticket;
- symbol;
- type;
- volume;
- price_open;
- SL/TP;
- open time;
- magic/comment;
- account/server scope;
- snapshot timestamp;
- source sequence.

The snapshots must preserve pre-existing same-symbol positions so the maximum-ticket heuristic can be tested rather than assumed.

#### History orders

Capture all related history orders with:

- order ticket;
- position_id if available;
- symbol;
- type;
- state;
- volume_initial;
- volume_current;
- time_setup;
- time_done;
- request/source identifiers;
- account/server scope.

#### History deals

Capture every related deal as a separate record with:

- deal ticket;
- order ticket;
- position_id;
- entry/exit flag or type;
- symbol;
- volume;
- price;
- profit;
- commission;
- swap;
- fee;
- timestamp;
- magic/comment;
- account/server scope;
- source sequence;
- retrieval batch ID.

### 23.4 Required case matrix

The bundle must explicitly mark each case as captured, not observed, or unavailable:

1. one order to one deal to one position;
2. one order to multiple entry deals;
3. partial fill or requested/filled volume mismatch;
4. partial close;
5. full close;
6. close followed by reopen on the same symbol;
7. multiple simultaneous positions on one symbol;
8. at least two account/server scopes;
9. repeated history retrieval for the same time range;
10. duplicate/replayed broker event.

A missing case must remain UNKNOWN. “Not observed” must not be changed to “impossible.”

### 23.5 Repeated retrieval format

For each repeated retrieval store a non-production record containing:

- capture_id;
- query_id;
- query type: history_orders or history_deals;
- account/server scope;
- start/end query window;
- retrieval timestamp;
- retrieval sequence number;
- pagination/cursor information;
- returned event IDs in returned order;
- event timestamps in returned order;
- payload digest per event;
- complete-response digest;
- overlap with prior retrieval;
- whether the source event was already observed.

This is required to distinguish source replay from application duplicate writes and to avoid assuming chronological list order.

### 23.6 Collision analysis

The bundle must contain at least two account/server scopes where available and preserve equality relationships for:

- same numeric order value across accounts;
- same numeric position value across accounts;
- same numeric deal value across accounts;
- same numeric value across identity types;
- reused values across separate lifecycle intervals.

Sanitization may replace raw values with stable relation tokens, but must preserve equality/inequality, account boundaries, identity type, and relative lifecycle order.

### 23.7 Activation evidence

To classify newer modules, collect only repository/deployment evidence such as:

- exact launcher command;
- process/service name;
- startup log marker;
- deployment manifest;
- import path from a running composition root;
- verified runtime configuration reference.

Source file presence, test imports, and importability checks alone must remain insufficient.

### 23.8 Acceptance interpretation

The acquisition bundle can resolve the Phase 15 blockers only if:

- all claimed broker facts have authoritative or complete scoped provenance;
- account mode is explicit;
- each identity has account/server and identity type;
- all related deals are retained individually;
- request/result/position snapshots are correlated;
- history ordering/replay behavior is captured or explicitly remains conservative;
- no finite sample is promoted to global uniqueness;
- maximum-ticket selection is either demonstrated per sequence or rejected as a canonical mapping;
- activation status is supported by runtime/deployment evidence.

## 24. Phase 16 gate

The minimum broker evidence dataset is not present. Existing records are application artifacts, synthetic behavior, incomplete aggregate evidence, or configuration; they do not resolve the critical broker identity questions.

PHASE 16 GATE: BLOCKED — INSUFFICIENT EVIDENCE

