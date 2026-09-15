# Phase 13 — Production Identity Evidence

## 1. Executive summary

This report is a read-only investigation of the production identity and
account behavior surrounding the legacy V3 execution path. It does not change
production code, persistence, configuration, or runtime state.

The repository proves that order, position, and deal identifiers are treated
as distinct concepts in newer execution value objects, but it does not prove
the broker namespace or uniqueness guarantees for their numeric values. The
legacy production path also does not preserve those identities separately:
`trades.ticket` receives either a position ticket or an order-ticket fallback,
depending on execution state, while exit handling uses `deal.position_id`.

The repository further proves that the legacy logger writes one trade row per
accepted entry and does not persist a per-deal execution lineage. Partial
fills, partial closes, duplicate observations, event ordering, and
multi-position/hedging behavior therefore cannot be reconstructed reliably
from the legacy record alone. Account login and server identify the MT5
connection, but the legacy entry write omits account scope and the legacy exit
update is ticket-only.

The critical production identity questions remain unresolved. The safest gate
is therefore:

**PHASE 13 GATE: BLOCKED — INSUFFICIENT EVIDENCE**

## 2. Evidence methodology

The investigation used repository source, existing characterization/design
artifacts, and static call-path tracing only. It inspected the legacy logger,
broker and auto-trader paths, newer execution identity/reconciliation code,
account abstractions, synchronization/orphan tooling, and relevant tests.

No live or file-backed database was opened. No MT5 terminal, broker, network,
cache, production configuration, or launcher was accessed. No orders,
positions, or production records were touched. Existing tests that use fake
MT5 objects or synthetic identifiers were treated as characterization of
application behavior, not as evidence of broker-wide identifier guarantees.

Conclusions use the required classifications:

- **PROVEN** — directly established by source, tests, or documentation.
- **STRONGLY INDICATED** — supported by multiple independent repository facts.
- **INFERRED** — a reasonable interpretation that is not guaranteed.
- **UNKNOWN** — repository evidence is insufficient.

## 3. Production execution identity flow

The verified legacy flow is:

```text
MT5 order_send result
    ↓ success
positions_get(symbol)
    ↓ positions exist
max(position.ticket)
    ↓ otherwise
result.order
    ↓
{'ticket': selected value}
    ↓
auto_trader_exness.py extracts dict['ticket']
    ↓
TradeLogger.log_trade_entry(..., ticket=value, no account)
    ↓
trades.ticket
    ↓ later position monitoring
newly_closed = previous_position_tickets - current_position_tickets
    ↓ history deals with entry == 1 and deal.position_id in newly_closed
ticket = deal.position_id
    ↓
TradeLogger.log_trade_exit(ticket=...)
```

In `broker_exness.py`, the successful pending-order request is submitted with
`mt5.order_send`. The broker first retries `None` results and transient error
codes according to the existing retry behavior. On success, the exchange
branch may use the maximum position ticket for a subsequent SL/TP
modification. The common successful return path then queries positions for the
symbol again and returns the maximum position ticket when any position is
found; otherwise it returns `result.order`.

In `auto_trader_exness.py`, the returned dictionary ticket is passed to
`log_trade_entry`. The current call does not pass `account=acc.name`, and it
does not persist separate order, position, or deal fields. The exit path does
not use `deal.ticket`; it uses `deal.position_id` after detecting that a
position ticket disappeared.

This is an observed code path. The repository cannot establish how frequently
each broker-return branch occurs in deployed production or whether the maximum
position ticket is always the newly created position.

## 4. Account-scope findings

### Observed fields and sources

| Field | Observed role | Produced/passed by | Legacy persistence use | Confidence |
|---|---|---|---|---|
| broker | broker/provider context | broker/account configuration and Phase 12 model | not stored by legacy `TradeLogger` | PROVEN |
| login/account number | MT5 account identity used for connection/verification | account configuration and MT5 login checks | not stored as a dedicated legacy column | PROVEN |
| server | MT5 server namespace/context | account configuration and connection | not stored by legacy `TradeLogger` | PROVEN |
| environment | configuration label such as demo/live | account configuration/newer `AccountContext` | not stored by legacy `TradeLogger` | PROVEN |
| account name | application label such as `Demo2`/`Live_Micro` | `AccountState.name` and query filters | legacy entry call omits it; newer queries can filter it | PROVEN |
| account_id | newer account abstraction identifier | `AccountConfig`/`AccountContext` | not part of the legacy base persistence contract | PROVEN |
| local account ID | proposed stable local scope | Phase 12 design | not present in legacy runtime | PROVEN |

The MT5 connection is operationally scoped by login/account number and server.
Broker, environment, and account name are configuration/application context,
not proven substitutes for that broker namespace. The current legacy logger
accepts an optional `account` string, but the current entry call does not pass
it and the exit call has no account argument. The repository therefore does
not prove that legacy rows are account-isolated.

The Phase 12 `AccountScope` design—broker, login, server, environment, and
optional local account ID—is an explicit future value model. It does not prove
that all of those fields can currently be populated from every legacy row.

### Account-scoped exit risk

`log_trade_exit(ticket=...)` selects and updates by `ticket` alone. It does not
include account, login, server, or environment in the lookup or update. If two
accounts have the same numeric legacy ticket, an exit can select the first
open matching row and update every matching row because the update predicate
is also ticket-only. This is a concrete cross-account risk if duplicate
numeric identifiers occur; the repository does not establish whether that
collision occurs in deployed accounts.

## 5. Order identity findings

`result.order` is the MT5 order identifier returned by the submission result
when the broker path falls back because no position was found. It is not stored
in a dedicated order column by the legacy logger. It can instead be stored in
the ambiguous `trades.ticket` field.

The newer `packages/execution/mt5_identity.py` model represents an order ticket
separately from position and deal tickets. That separation is a design/value
model, not evidence that the legacy `trades.ticket` value is an order ticket.

The repository has no proof that order tickets are unique globally, per
account, per account/server, or under another broker namespace. **Repository
evidence is insufficient.**

## 6. Position identity findings

`positions_get(symbol=...)` returns position objects whose `.ticket` is used by
the broker return path and by current-position snapshots. The auto-trader
uses those position tickets to detect disappeared positions. The exit history
path compares `deal.position_id` with the disappeared position-ticket set and
passes that position reference to `log_trade_exit`.

`orphan_detector.py` directly compares an MT5 position `.ticket` with
`trades.ticket`, which assumes the legacy ticket is a position ticket. That is
not safe for rows created through the `result.order` fallback. The newer
reconciler is position-scoped and uses `position_id` references, but it is not
proof that legacy rows preserve a typed position identity.

The repository has no proof of global or account-scoped uniqueness for numeric
position tickets, and no proof of the active account's netting/hedging mode.

## 7. Deal identity findings

`deal.ticket` is the deal identifier in MT5 history. `deal.position_id` is a
reference to the position associated with that deal, not the deal identity.
The exit path uses `deal.position_id` as the legacy lookup ticket and does not
persist `deal.ticket`.

The newer identity model and `mt5_reconciler.py` preserve deal ticket values in
typed/in-memory evidence structures. The legacy schema does not have separate
entry-deal or exit-deal columns. Multiple deals can therefore not be
represented as separate legacy execution events.

The repository has no proof of deal-ticket uniqueness globally, per account,
or per account/server, and no proof of a stable event-id/idempotency contract.

## 8. Legacy `trades.ticket` findings

`trades.ticket` is a nullable, legacy broker-identifier field. Its value may
represent:

1. the maximum position ticket found after a successful order submission; or
2. `result.order` when no position is found at the broker-return point.

It may therefore represent an MT5 position ticket or an MT5 order ticket
depending on execution path. It is not a consistently typed order, position,
or deal identity. It must remain opaque until an execution-path-specific
mapping is proven.

The legacy logger permits duplicate values and nullable values. Its exit
lookup uses the opaque numeric value, selects one open row for the PnL
calculation, and then updates all rows whose `ticket` matches. It does not
scope by account. A missing ticket produces a silent no-op. These behaviors
are directly established by `risk/trade_logger.py` and prior characterization
artifacts.

## 9. Entry-fill findings

The current production entry call creates one legacy trade record after an
accepted broker result. It passes the requested pair, signal, confidence,
planned entry/SL/TP data from the signal, requested volume, regime, and the
single selected legacy ticket value.

The legacy row does not preserve:

- `result.order` in a dedicated order field;
- `result.deal` in a dedicated entry-deal field;
- one row per entry deal;
- per-deal execution price or quantity;
- source event IDs or idempotency keys;
- a complete order-to-position-to-deal lineage.

If an order is filled through multiple deals, the legacy logger still has only
the one entry row created by the auto-trader call. A rejected/failed order
does not reach that entry log call. The repository cannot prove the number of
real fills in a live account or whether the selected maximum position ticket
corresponded to the newly accepted entry.

The newer `TradeIdentity.reconcile_with_mt5` can hold one entry-deal value and
actual entry data, but repeated entry deals overwrite the single entry-deal
slot. `mt5_reconciler.py` likewise assigns the last observed entry deal to its
single `entry_deal` field. These newer structures do not establish complete
legacy lineage support.

## 10. Partial-close findings

The auto-trader detects a close when a previously observed position ticket is
absent from the current position set. While a position remains open after a
partial close, this disappearance condition is not met, so the current path
does not log the partial exit at that point.

When a position disappears, the code scans recent history deals and processes
deals with `entry == 1` whose `position_id` is in the disappeared set. It passes
the position reference—not `deal.ticket`—to `log_trade_exit`. A legacy row has
one `exit_price`, `exit_time`, `pnl`, `pnl_percent`, `result`, and `reason`
state. Repeated matching events can overwrite the same ticket-matched rows,
subject to the logger's broad ticket-only update behavior.

The legacy schema cannot represent one position with independent exit deals A,
B, and C without losing deal-level identity, quantity, price, and event
ordering. `mt5_reconciler.py` retains a `partial_deals` list in memory, but
that is not a legacy persistence guarantee and is not a complete idempotent
event ledger.

## 11. Multi-position and hedging findings

The auto-trader performs position-existence, opposite-position, exposure,
correlation, and hedge-related checks. Its broker return path nevertheless
selects the maximum position ticket among all positions for the symbol, rather
than proving that the selected position is the one created by the submitted
order.

The repository contains newer per-account worker/account-context abstractions,
but they are not the verified legacy V3 path. It does not prove whether the
deployed account is netting or hedging, whether one strategy-level trade can
create multiple positions, how close-and-reopen sequences are linked, or how
multiple simultaneous positions for a symbol are represented in legacy
persistence.

Therefore the following are **UNKNOWN** from repository evidence:

- active account mode (netting versus hedging);
- guaranteed one-order/one-position behavior;
- position recreation lineage;
- close-and-reopen disambiguation;
- complete multi-position persistence.

## 12. Event ordering and idempotency findings

MT5 history objects expose candidate evidence fields including `deal.ticket`,
`deal.position_id`, deal time, symbol, volume, price, profit, commission,
swap, entry flag, and reason. Order requests also include fields such as magic
number and comment. The newer account-manager path can expose separate
`order_ticket`, `position_ticket`, and `deal_ticket` values.

The legacy persistence path does not store a source event ID, event type,
deal ticket, order ticket, position ticket, broker login/server namespace, or
idempotency key. The auto-trader history loop has no explicit event sorting or
deduplication contract. The reconciliation code does not establish a stable
ordering/idempotency protocol, and a single-value entry/exit representation
cannot preserve repeated partial events.

Consequently, the repository cannot reliably distinguish a duplicate
observation from a legitimate repeated execution, retry, delayed event, or
out-of-order event. `deal.ticket` is a candidate source event identifier for a
future design, but its namespace and production uniqueness are unproven and
the current code does not use it as an idempotency key.

## 13. Evidence table

| Question | Finding | Evidence | Confidence | Proven? |
|---|---|---|---|---|
| MT5 order-ticket namespace | Global, per-account, and per-account/server uniqueness are not established. | No repository namespace specification; `mt5_identity.py` separates types but does not assert uniqueness; synthetic MT5 tests use distinct sample numbers only. | UNKNOWN | No |
| MT5 position-ticket namespace | Position `.ticket` is used as a position reference in several paths, but uniqueness scope is not established. | `broker_exness.py`, `auto_trader_exness.py`, `orphan_detector.py`, `mt5_reconciler.py`. | UNKNOWN | No |
| MT5 deal-ticket namespace | `deal.ticket` is a deal identifier in history, but uniqueness scope and event guarantees are not established. | MT5 history consumers and newer identity model; no persisted event key or namespace proof. | UNKNOWN | No |
| Successful legacy entry ticket | Position ticket is selected when symbol positions exist; otherwise `result.order` is selected. | `ai-service/broker_exness.py` success return branches. | PROVEN | Yes, for code behavior |
| Legacy entry persistence | One `log_trade_entry` call writes one row with one opaque ticket value. | `ai-service/auto_trader_exness.py`, `risk/trade_logger.py`. | PROVEN | Yes |
| Legacy ticket type | `trades.ticket` can be a position ticket or an order-ticket fallback; it is not typed. | Broker return flow and logger schema. | PROVEN | Yes |
| Exit identifier | The auto-trader passes `deal.position_id`, not `deal.ticket`, to `log_trade_exit`. | `ai-service/auto_trader_exness.py` close-history branch. | PROVEN | Yes |
| Exit account scoping | Legacy exit matching and update use ticket only. | `risk/trade_logger.py::log_trade_exit`. | PROVEN | Yes |
| Entry-deal persistence | Legacy logger does not preserve each entry deal or a deal ticket. | Legacy schema and entry call; no deal columns. | PROVEN | Yes |
| Partial-entry reconstruction | Complete multi-deal entry lineage cannot be reconstructed from the legacy row. | One-row entry persistence and absent per-deal fields. | STRONGLY INDICATED | No live-fill proof |
| Partial-close persistence | A single legacy row cannot preserve multiple exit deals independently. | Single exit fields in `trades`; `mt5_reconciler.py` only keeps an in-memory list. | PROVEN | Yes for schema capability |
| Multiple-position semantics | Active netting/hedging mode and complete position linkage are not established. | Position checks and max-ticket selection; no deployed account-mode proof. | UNKNOWN | No |
| Account authority | Login/account number plus server scope the MT5 connection; legacy row account is optional and omitted by current entry call. | Account configuration/context, `AccountState`, auto-trader call, `TradeLogger`. | PROVEN | Yes for observed code |
| Event idempotency | No stable persisted event key or dedupe/order protocol is established. | No deal/order/source-event columns; history/reconciliation loops lack explicit dedupe. | PROVEN | Yes for absence; guarantees UNKNOWN |
| Production branch frequency | Repository cannot establish how often position-ticket versus `result.order` fallback occurs live. | No production runtime evidence was accessed. | UNKNOWN | No |

## 14. Confidence by major conclusion

| Major conclusion | Classification | Reason |
|---|---|---|
| `trades.ticket` is ambiguous between a position ticket and an order fallback. | PROVEN | The broker success branches and auto-trader assignment are directly visible. |
| Exit handling uses a position reference (`deal.position_id`) rather than deal identity. | PROVEN | The close-history call path assigns and passes `deal.position_id`. |
| Legacy exit updates are not account-scoped. | PROVEN | The logger SQL predicates contain only `ticket`. |
| Legacy persistence does not preserve complete deal lineage. | PROVEN | No per-deal identity/quantity/event fields are written by the legacy path. |
| Numeric MT5 identifiers are unique globally or within a specific account namespace. | UNKNOWN | Repository evidence is insufficient. |
| Real production partial-fill behavior is fully represented by the legacy path. | UNKNOWN | No live broker evidence is permitted or available, and the schema lacks deal-level records. |
| Active account mode and multi-position behavior are known. | UNKNOWN | Code contains guards and abstractions but no account-mode/runtime proof. |
| Current system can distinguish duplicates, retries, and out-of-order events. | UNKNOWN | No stable persisted event identity or ordering protocol is present. |
| Login plus server are the strongest observed broker account scope. | STRONGLY INDICATED | They are used for MT5 connection/account verification, while labels are configuration context. |

## 15. Unresolved questions

The following require evidence not available from repository source alone:

1. Whether order, position, and deal numeric identifiers are unique globally,
   per login, per login/server, or under another MT5 namespace.
2. Whether the deployed accounts are netting or hedging accounts.
3. Whether the maximum position ticket returned by the broker path is reliably
   the position created by the submitted order.
4. Whether live orders commonly produce multiple entry deals or partial
   closes in this system.
5. Whether separate accounts can produce colliding numeric tickets in the
   actual deployment.
6. Whether duplicate history observations occur and how broker history is
   ordered in all runtime conditions.
7. Whether any operational process outside the inspected repository writes or
   repairs the legacy trades table.
8. Whether newer reconciliation tools are active in production or are
   experimental/diagnostic only.
9. Whether production processes or threads concurrently share the same
   SQLite connection beyond the observed shared logger construction.

## 16. What is proven

- The legacy broker return value has a position-ticket branch and an
  `result.order` fallback branch.
- The legacy auto-trader stores that selected value in `trades.ticket` without
  preserving its type.
- The current close path uses `deal.position_id` as the legacy lookup value,
  not `deal.ticket`.
- Legacy entry writes are single-row and legacy exit writes are broad,
  ticket-only updates with no account predicate.
- The legacy schema has no independent order, position, entry-deal, exit-deal,
  event-id, or reconciliation-lineage columns.
- Newer execution value objects distinguish order, position, and deal types,
  but do not retrofit those distinctions into legacy persistence.
- The repository contains direct consumers that make incompatible assumptions,
  including a position-ticket comparison against `trades.ticket`.

## 17. What is NOT proven

- Any global or account/server uniqueness guarantee for MT5 numeric IDs.
- That `trades.ticket` is always a position ticket, always an order ticket, or
  ever a deal ticket.
- That one order creates one position or one deal in the deployed account.
- That partial fills and partial closes are fully captured or reconstructable.
- That active accounts use netting or hedging mode in all deployments.
- That ticket-only exit matching is safe across accounts.
- That history event order is stable or that duplicate observations are
  deduplicated.
- That the current legacy row can support production reconciliation without a
  separate typed identity/event model.

## 18. Recommendation for the next phase

Do not implement production identity mapping, account-scoped exit changes, or
schema changes yet. The next design/evidence phase should obtain a safe,
non-mutating execution evidence set—such as approved historical MT5 export or
sanitized recorded responses—with explicit account/server scope and order,
position, deal, and timestamp fields. It should also verify active account
mode, multi-fill/partial-close examples, and event duplication/order before
any canonical persistence or reconciliation contract is implemented.

That evidence work must remain isolated from live execution and must not
reinterpret legacy `trades.ticket`. Until those questions are answered, keep
the Phase 10 façade and Phase 12 identity model as design/characterization
artifacts only; do not wire them into production.

## 19. Evidence classification summary

| Area | Result |
|---|---|
| Production broker return branch | PROVEN from source |
| Legacy ticket ambiguity | PROVEN from source |
| Legacy exit identifier assignment | PROVEN from source |
| Legacy account omission/ticket-only exit | PROVEN from source |
| Deal-level lineage support | PROVEN absent in legacy schema; live completeness UNKNOWN |
| MT5 namespace uniqueness | UNKNOWN — Repository evidence is insufficient. |
| Account mode and multi-position behavior | UNKNOWN |
| Event idempotency/order guarantees | UNKNOWN |
| Safe production identity mapping | UNKNOWN |

PHASE 13 GATE: BLOCKED — INSUFFICIENT EVIDENCE
