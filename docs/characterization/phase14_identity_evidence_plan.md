# Phase 14 — Identity Evidence Plan

## 1. Purpose and safety boundary

This document defines the smallest safe evidence collection needed to resolve
the UNKNOWN findings from Phase 13. It is a read-only planning artifact. It
does not create an identity mapping, change `trades.ticket`, alter persistence,
or authorize production wiring.

The collection plan must not use credentials, place orders, modify positions,
write to production databases, or change runtime configuration. Evidence must
be obtained from existing repository artifacts, approved sanitized historical
exports, or isolated recorded/synthetic responses. A live MT5 session is not
required by this plan and is not authorized by Phase 14.

## 2. Phase 13 findings being resolved

Phase 13 proved the following application behavior:

- `broker_exness.py` returns the maximum symbol position ticket when positions
  are visible after submission and otherwise falls back to `result.order`.
- `auto_trader_exness.py` stores that value as the opaque legacy
  `trades.ticket` field.
- The close path passes `deal.position_id` to `log_trade_exit(ticket=...)`, not
  `deal.ticket`.
- Legacy entry persistence creates one row and does not persist per-deal
  lineage, source event IDs, or typed order/position/deal fields.
- Legacy exit matching is ticket-only and not account-scoped.
- Newer identity/reconciliation code separates identity types but does not
  prove broker namespace guarantees or production activation.

The following remain UNKNOWN and are the scope of this plan:

1. order-ticket namespace and uniqueness scope;
2. position-ticket namespace and uniqueness scope;
3. deal-ticket namespace and uniqueness scope;
4. active account mode: netting or hedging;
5. one-order/multiple-deal and partial-fill behavior;
6. partial-close and close-and-reopen lineage;
7. numeric identifier collisions across accounts;
8. broker history ordering and replay behavior;
9. event idempotency requirements;
10. correlation between maximum-position-ticket selection and the submitted
    order;
11. whether newer reconciliation/account-context code is active or
    diagnostic only.

## 3. Evidence classes

Evidence must be labeled by source class. These classes must not be combined
silently:

| Class | What it can establish | What it cannot establish by itself |
|---|---|---|
| Repository source | Exact application assignments, persistence fields, branches, and absent behavior. | Broker-wide uniqueness, actual account mode, live fill frequency, or production activation. |
| Existing characterization tests | Deterministic behavior of fakes, adapters, and pure value objects. | Real MT5 semantics or live production outcomes. |
| Recorded/synthetic MT5 responses | Whether the application handles a specified order/result/position/deal sequence and whether a branch correlates identifiers. | Broker guarantees beyond the captured scenarios. |
| Sanitized historical MT5 export | Observed identifiers, account boundaries, fill/close events, ordering, and relationships in a bounded period. | A universal uniqueness guarantee unless the export is authoritative and its scope is documented. |
| Authoritative broker/MT5 documentation | Published identifier meaning, account scope, account mode semantics, and documented lifecycle rules. | Whether this application actually received/used values as documented in every runtime path. |
| Runtime activation evidence | Whether a module, daemon, reconciler, or account abstraction is actually started and used. | Broker namespace semantics or correctness of the active code. |

No finite sample should be described as proof of global uniqueness. A finite
sample can prove non-collision only within its documented sample scope. A
namespace guarantee requires authoritative semantics or an explicit
conservative design rule that does not depend on unproven uniqueness.

## 4. Evidence requirements by question

The following table is the collection contract. “Repository sufficient” means
the existing repository can answer the question without external execution;
it does not mean the repository contains no relevant code.

| Exact question | Evidence required and acceptable source | Repository sufficient? | Sanitized historical export required? | Recorded/synthetic responses sufficient? | Live MT5 required? | Fields that must be captured | Interpretation and PROVEN threshold |
|---|---|---:|---:|---:|---:|---|---|
| What namespace owns `order.ticket` and is it unique? | Official MT5/broker identifier documentation plus bounded history containing account/server scope and order records. | No | Preferred | Insufficient for broker guarantee; sufficient for application branch tests. | No for minimum plan | broker, login alias, server alias, environment, order ticket token, order time, symbol, request correlation, result code | PROVEN only if authoritative documentation states scope/uniqueness or the canonical design explicitly treats the identifier as scoped and does not assume stronger uniqueness. A sample alone leaves global uniqueness UNKNOWN. |
| What namespace owns `position.ticket` and is it unique? | Account-mode metadata and position/history export with position tickets across accounts and lifecycle events. | No | Required for observed behavior | Insufficient for universal guarantee; sufficient for position-reference handling. | No for minimum plan | account scope, position ticket token, open/close times, symbol, volume, related deals | PROVEN only for documented broker scope or explicitly bounded dataset scope. Otherwise retain account+type scoping and mark global uniqueness UNKNOWN. |
| What namespace owns `deal.ticket` and is it unique? | Authoritative identifier semantics plus history deals from multiple accounts and event windows. | No | Required | Synthetic data can prove typed separation and dedupe rules, not broker guarantees. | No for minimum plan | deal ticket token, account scope, order ticket if present, position_id, entry/exit, time, volume | PROVEN only for the documented namespace. `deal.position_id` must remain a position reference, never a deal identity. |
| Are numeric identifiers colliding across accounts? | At least two account-scoped exports with preserved equality/inequality relationships, or authoritative namespace documentation. | No | Required if collision evidence is sought | Synthetic collisions prove the model rejects conflation, not actual broker collisions. | No | account scope, identity kind, numeric-value relation token, lifecycle interval | A collision is PROVEN when the same numeric value appears under different account/type scopes in trusted evidence. Absence of collision in a sample is not proof of uniqueness. |
| Is each account netting or hedging? | Sanitized `account_info`/configuration snapshot with margin mode and server/account scope, or authoritative account metadata. | No | Required unless authoritative snapshot exists | Synthetic mode fixtures test application behavior only. | No for minimum plan | login alias, server alias, environment, margin mode, account mode source, capture time | PROVEN only when mode is explicitly reported by MT5/account metadata or authoritative configuration for the deployed account. |
| Can one order produce multiple entry deals? | Correlated order request/result/history export containing one order and all associated entry deals. | No | Required | Recorded responses are sufficient for application behavior if complete; synthetic is not proof of live occurrence. | No if complete recording exists | order ticket, deal tickets, position_id, entry flag, volumes, prices, timestamps, retcodes | PROVEN for a captured sequence when all associated deals are present and correlation is explicit. Otherwise UNKNOWN. |
| How are partial fills represented? | Multi-deal order sequence with requested volume, each deal volume, cumulative volume, and resulting position state. | No | Required | Synthetic responses validate lineage representation but not production frequency. | No | requested volume, deal volume, cumulative volume, remaining volume, order/position/deal IDs | PROVEN only when quantities reconcile within documented rounding and all deals are captured. |
| How are partial closes represented? | One position with multiple exit deals, position snapshots before/after each event, and complete history window. | No | Required | Recorded/synthetic responses can establish consumer handling; real export is required to prove occurrence. | No if historical evidence exists | position ticket, exit deal tickets, position_id, exit volumes/prices/times, remaining volume, close reason | PROVEN when exit quantities and remaining position state show the partial-close sequence. A single final row is insufficient. |
| How is close-and-reopen lineage represented? | Ordered export containing close event, position disappearance, new order/position, and any reused numeric values. | No | Required | Synthetic sequence can prove proposed lineage semantics only. | No | old/new position IDs, close deal, new order/deals, timestamps, symbol, account scope, strategy correlation if present | PROVEN only if the event sequence explicitly distinguishes old and new positions. Same symbol or same numeric value is not sufficient. |
| What is broker history ordering? | Repeated retrieval recordings or an export preserving source sequence and event timestamps, with pagination/window metadata. | No | Preferred | Synthetic permutations test order-independent processing but cannot prove broker ordering. | No for minimum plan | retrieval time, query window, page/cursor if any, event sequence index, event timestamp, deal ticket | PROVEN only for the observed retrieval contract. Timestamp ordering must not be assumed from list order without evidence. |
| Are history observations duplicated or replayed? | Same event observed across repeated retrievals or overlapping windows with stable source identifiers. | No | Required | Synthetic duplicate fixtures test idempotency requirements, not occurrence. | No | source event/deal ticket, retrieval batch, first/last seen, payload hash, event timestamp | PROVEN when the same source event appears more than once or authoritative API behavior documents replay. Without stable event identity, dedupe remains UNKNOWN. |
| What idempotency key is available? | Complete event records showing stable deal/order identity and account/type scope across repeated observations. | No | Required | Synthetic data can test candidate keys and conflict behavior. | No | account scope, identity kind, ticket, source event ID, payload hash, event time | PROVEN only for the stable scoped source identifier; otherwise require an explicit future event key and keep reconciliation blocked. |
| Does maximum-position-ticket selection correlate with submitted order? | Time-correlated recordings of request, result, positions before/after, and selected position, including pre-existing same-symbol positions. | No | Required if historical recordings exist | Yes for branch/correlation tests, but not for production frequency. | No for minimum plan | request correlation, result.order/deal, positions before/after with tickets, selected max ticket, symbol, timestamps | PROVEN only per captured sequence. A maximum ticket heuristic cannot be promoted to a general mapping without repeated evidence and a safe fallback. |
| Is newer reconciliation/account-context code production-active? | Launcher/process configuration history, deployment manifests, startup logs, import/runtime evidence, and source activation references. | Partially | Not necessarily | Synthetic imports do not prove activation. | No | module, entry point, process, launch command, account config source, activation timestamp, log marker | PROVEN active only with startup/runtime evidence. Source presence alone is not enough; absence from inspected launchers leaves status UNKNOWN. |

## 5. Non-mutating sanitized execution-record template

The following JSONL-style record is a template, not a production schema. It
must be stored outside production databases and contain no credentials,
passwords, account secrets, access tokens, or raw personally identifying
metadata. One file may contain multiple `event` records plus one `capture`
record.

```json
{
  "record_type": "execution_evidence",
  "schema_version": "phase14.v1",
  "capture": {
    "capture_id": "CAPTURE_A01",
    "source_class": "sanitized_historical_export",
    "source_system": "MT5",
    "capture_window_start_utc": "2025-01-01T00:00:00Z",
    "capture_window_end_utc": "2025-01-31T23:59:59Z",
    "completeness": "documented_complete_for_window",
    "secrets_removed": true
  },
  "account_scope": {
    "broker": "broker_alias_1",
    "login_alias": "ACCOUNT_A",
    "server_alias": "SERVER_DEMO",
    "environment": "demo",
    "local_account_alias": "LOCAL_A"
  },
  "order": {
    "order_ticket": "ORDER_NUM_001",
    "order_numeric_relation": "NUM_001",
    "order_timestamp_utc": "2025-01-10T10:00:00.000Z",
    "symbol": "PAIR_ALIAS",
    "side": "BUY",
    "requested_volume": 1.0,
    "magic_alias": "MAGIC_X",
    "comment_alias": "COMMENT_X",
    "request_correlation_id": "REQ_001",
    "result_code": "SUCCESS"
  },
  "entry_execution": [
    {
      "deal_ticket": "DEAL_NUM_001",
      "deal_numeric_relation": "NUM_101",
      "position_id": "POSITION_NUM_001",
      "position_numeric_relation": "NUM_201",
      "execution_timestamp_utc": "2025-01-10T10:00:00.100Z",
      "execution_volume": 0.4,
      "execution_price": 1.10001,
      "entry_flag": "ENTRY_IN",
      "deal_type_alias": "BUY",
      "deal_reason_alias": "EA",
      "source_sequence": 1
    }
  ],
  "position_lifecycle": {
    "position_ticket": "POSITION_NUM_001",
    "position_numeric_relation": "NUM_201",
    "open_time_utc": "2025-01-10T10:00:00.100Z",
    "close_time_utc": null,
    "remaining_volume_after_event": 0.4,
    "close_reason_alias": null
  },
  "exit_execution": [],
  "observation": {
    "retrieval_batch_id": "BATCH_001",
    "retrieval_sequence": 1,
    "observed_at_utc": "2025-01-10T10:01:00Z",
    "payload_hash": "HASH_ALIAS_001",
    "replay_of_event": null,
    "source_complete": true
  }
}
```

For a partial close, `exit_execution` contains one object per exit deal and
`position_lifecycle.remaining_volume_after_event` is recorded after each
event. For a multi-fill entry, `entry_execution` contains one object per deal;
the requested volume remains on the order object and must not be substituted
for actual deal volume. For an order without a position, the position fields
remain null and the reason is recorded as an observed outcome, not inferred.

Required optional fields for difficult cases include:

- `order_result_deal_ticket` when returned by the recorded result;
- `position_snapshot_before` and `position_snapshot_after`;
- `event_kind` (`order_result`, `entry_deal`, `exit_deal`, `position_snapshot`);
- `event_source_id` when supplied by the source;
- `source_sequence` and `retrieval_sequence`;
- `reconciliation_status` as an observation label only;
- `missing_reference` describing an absent order, position, or local record.

These fields describe evidence; they do not define a production database
schema or authorize persistence changes.

## 6. Sanitization and anonymization rules

Sanitization must preserve relationships while removing secrets:

1. Replace login/account numbers, broker names, and servers with stable aliases
   (`ACCOUNT_A`, `SERVER_1`). Preserve equality and inequality relationships.
2. Preserve account boundaries. Do not merge accounts into one anonymous scope.
3. Replace numeric identifiers with stable relation tokens. Preserve whether
   two source fields had the same numeric value, while retaining explicit
   identity kind and account scope. For example, the same `NUM_001` may appear
   as an order and position value only if that equality existed in source;
   the typed fields must still remain distinct.
4. Never use a hash process that silently collapses values or loses the
   distinction between identity types.
5. Shift timestamps by a documented fixed offset per capture or account while
   preserving relative ordering, event deltas, and close/reopen sequence.
6. Preserve requested and execution quantities, cumulative quantities, and
   remaining quantities. If scaling is required, use one documented factor
   for all quantities in a capture and preserve sums/ratios.
7. Normalize prices only through a documented deterministic transform that
   preserves equality and ordering. Do not replace actual price with a
   rounded value that changes fill relationships.
8. Replace magic numbers/comments with aliases while preserving equality,
   repeated-use relationships, and whether the field was absent.
9. Remove credentials, passwords, tokens, terminal paths, hostnames, account
   names that reveal personal information, and unrelated symbols/strategy
   details. Preserve symbol identity only through a stable alias.
10. Include capture completeness, source window, and sanitization metadata.
    An incomplete export must not be treated as a complete event history.

## 7. Minimum evidence dataset to unblock Phase 13

The minimum safe dataset is a bounded, sanitized, read-only evidence bundle,
not unrestricted production access. It should contain:

1. One complete single-fill entry and full close sequence.
2. One order-result sequence where positions are absent and the
   `result.order` fallback is selected.
3. One sequence with pre-existing same-symbol positions, showing whether the
   maximum-ticket selection is correlated with the submitted request.
4. One multi-deal entry or an authoritative statement that the captured
   account/order model cannot produce it.
5. One partial-close sequence with at least two exit deals, or an authoritative
   statement that the relevant account mode/API semantics prevent it.
6. One close-and-reopen sequence with ordered old and new identities.
7. One repeated/overlapping history retrieval showing duplicate/replay
   behavior, or a documented source guarantee with the exact scope.
8. Account metadata for at least two account scopes when available, including
   server and environment aliases and explicit netting/hedging mode.
9. A collision analysis across the bundle for order, position, and deal
   numeric relations, including any equal values across accounts or identity
   types.
10. The exact retrieval window, pagination behavior, completeness statement,
    and source sequence metadata.
11. Activation evidence for newer reconciliation/account-context code: launch
    configuration, process evidence, or an explicit verified finding that it
    is diagnostic only.

If a scenario does not occur in the bounded evidence, record “not observed”;
do not convert that absence into a uniqueness or impossibility claim.

## 8. Interpretation rules

The evidence review must produce separate conclusions for:

- **Broker fact:** what MT5/broker documentation or source export establishes.
- **Application fact:** what the repository code does with the broker values.
- **Synthetic behavior:** what an isolated fake response proves about code
  handling only.
- **Inference:** a plausible explanation that is not safe to encode.

The following conclusions are acceptable:

- If authoritative evidence establishes that an identifier is scoped by
  account/server and identity type, the canonical model may use that scope;
  it must still keep order, position, and deal types distinct.
- If the namespace guarantee is absent, the canonical design must retain
  account scope, identity type, lifecycle/source context, and explicit
  uncertainty. It must not rely on bare numeric equality.
- If partial fills or closes are observed, each deal must remain a separate
  execution event in the future evidence/reconciliation model. One legacy
  `trades` row must not be treated as a complete event ledger.
- If no duplicate/replay guarantee exists, idempotency must be designed as an
  explicit future requirement rather than inferred from `deal.ticket` alone.
- If maximum-ticket selection is not correlated in recorded sequences, it must
  remain a legacy heuristic and cannot become a canonical mapping.
- If activation evidence is absent, newer reconciliation/account-context code
  remains non-production/unknown regardless of its source location.

## 9. PASS / BLOCKED criteria for the next gate

### PASS — evidence collection complete

The next gate may be marked ready for a design decision only when:

- the evidence source, scope, completeness, and sanitization are documented;
- account mode is explicitly established for every account considered;
- order, position, and deal identifiers have documented meaning and scope, or
  the design explicitly preserves them as scoped/possibly reusable values;
- collision relationships across accounts and identity types are analyzed;
- at least one complete order-to-entry-to-position sequence is available;
- partial fills, partial closes, and close/reopen cases are either captured or
  explicitly documented as not observed/unsupported;
- duplicate/replay and ordering behavior is characterized or remains an
  explicit conservative requirement;
- maximum-position-ticket selection is correlated or formally rejected as a
  canonical mapping;
- activation status of newer identity/reconciliation code is established;
- no conclusion depends on interpreting `trades.ticket` as a typed identity;
- no live state was changed and no production database/schema was touched.

PASS does not mean production migration is approved. It means the evidence is
sufficient to design the next canonical identity/reconciliation boundary.

### BLOCKED — evidence plan or dataset incomplete

Remain blocked if any of the following occurs:

- only synthetic identifiers are available for a broker-fact question;
- account/server scope is missing from execution records;
- the export cannot distinguish order, position, and deal fields;
- event completeness or retrieval ordering is unknown for the claimed window;
- partial fills/partial closes are inferred from one aggregate row;
- a sample is used to claim global uniqueness;
- the maximum-ticket correlation cannot be assessed;
- activation status is inferred from file presence alone;
- sanitization destroys equality, ordering, quantity, or account relationships;
- any evidence collection requires modifying live state or production storage.

## 10. Required evidence report format

The evidence collection report should include one row per question using:

| Question | Source class | Capture scope | Observed facts | Interpretation | Confidence | Proven? | Remaining UNKNOWN |
|---|---|---|---|---|---|---|---|

It must attach or reference only sanitized, non-secret evidence. It must list
missing scenarios explicitly and distinguish “not observed” from “impossible”.

## 11. Recommendation and phase boundary

Phase 14 is ready to enter evidence collection, but no identity mapping or
production persistence implementation is authorized. Evidence collection
should begin with existing sanitized exports or recorded responses. If those
do not exist, the project should first obtain an approved non-mutating capture
from a controlled environment, with no order submission and no production
state changes.

After evidence review, the next design phase should decide whether the
canonical identity model can be scoped by account/type alone, requires event
lineage/source identity, or must retain additional uncertainty. It must not
retrofit a meaning onto legacy `trades.ticket`.

PHASE 14 GATE: READY FOR EVIDENCE COLLECTION
