# Phase 12 Canonical Identity and Account Model Design

## Status

Design and characterization only. No production runtime, database, schema,
MT5, broker, network, cache, configuration, launcher, or legacy persistence
code was changed.

The new value types in
`packages/execution/canonical_execution_identity.py` are pure Python. They do
not import `MetaTrader5`, `broker_exness`, `auto_trader_exness`,
`risk.trade_logger`, or any persistence module.

## Repository evidence

### Current account abstractions

The legacy auto-trader has `AccountState.name`, broker account/login, and
server values, but shares one `TradeLogger` across account states. The entry
logging call does not pass `account=acc.name`, and the exit call has no account
argument.

The newer `packages/execution/account_context.py` defines an immutable
`AccountContext` with account ID, account name, environment, and broker server.
`packages/execution/account_manager.py` defines a newer worker model with one
account configuration per worker. Neither abstraction is the current
`auto_trader_exness.py` persistence contract.

Therefore account scope is supported as a design requirement, but current
legacy writes do not prove that every persisted row has complete account
identity.

### Current MT5 identity sources

| Source | Observed value | Meaning |
|---|---|---|
| `MT5Broker.place_market_order` | `result.order` | MT5 order ticket |
| `MT5Broker.place_market_order` after `positions_get` | `position.ticket` | MT5 position ticket, selected from the maximum symbol position ticket |
| `auto_trader_exness.py` position snapshot | `position['ticket']` | MT5 position ticket |
| `auto_trader_exness.py` close history | `deal.position_id` | Position identifier associated with an exit deal |
| MT5 history deal | `deal.ticket` | MT5 deal ticket |
| `risk/trade_logger.py` | `trades.id`/`lastrowid` | Local SQLite record identity |
| `risk/trade_logger.py` | `trades.ticket` | Ambiguous legacy broker identifier |

`packages/execution/mt5_identity.py` already distinguishes order, position,
entry-deal, and exit-deal tickets. `packages/execution/mt5_reconciler.py`
queries deal history by position ticket and represents partial deals. These
are repository evidence for separation, but they are not integrated into the
legacy logger.

### Current reconciliation limitations

- `auto_trader_exness.py` passes `deal.position_id` to legacy
  `log_trade_exit(ticket=...)`.
- `broker_exness.py` may place a position ticket or `result.order` into the
  legacy `ticket` value.
- `sync_positions.py` matches exit deals by symbol and nearest timestamp, then
  updates by local SQLite record ID.
- `orphan_detector.py` compares MT5 position tickets to `trades.ticket`.
- `mt5_reconciler.py` has a position-scoped model but is not the legacy
  production persistence path.

The repository does not prove a universal conversion from legacy ticket to any
typed identity.

## Canonical model

### `AccountScope`

The proposed account namespace contains:

- broker;
- MT5 login/account number;
- server;
- environment;
- optional stable local account identifier.

Values are explicit and compared exactly. The value type performs no casing,
alias, environment, or account-name normalization.

The account scope is part of the identity key for every typed order, position,
and deal.

### Typed identities

The model keeps these types distinct:

- `OrderIdentity(account, ticket_id)`;
- `PositionIdentity(account, ticket_id)`;
- `DealIdentity(account, ticket_id, role, position?)`;
- `TradeRecordId(value)` for local persistence identity.

Equal numeric values do not make different types equal. Account scope is also
part of equality, so the following remain distinct:

```text
Account A / Order 123
Account A / Position 123
Account A / Deal 123
Account B / Order 123
```

### Legacy ticket representation

`LegacyTicketValue` is an opaque compatibility value only. It has no conversion
method and no order, position, or deal type. It must not be placed into a typed
identity field without separately proven evidence for that operation.

## Identity lineage

`ExecutionLineage` represents references without performing reconciliation:

```text
local trade record (optional)
        │
        ├── order (optional)
        ├── position (optional)
        ├── zero or more entry deal observations
        └── zero or more exit deal observations
```

The model permits:

- order without position;
- position without order;
- deal without a locally known position;
- missing local trade record;
- multiple entry deals for partial fills;
- multiple exit deals for partial closes;
- duplicate deal observations;
- out-of-order observations;
- incomplete quantity, price, timestamp, or source-event data.

It preserves observation order as supplied. It does not sort, deduplicate,
choose a winner, calculate a close state, or reconcile with MT5. Those belong
to a future reconciliation boundary.

`DealExecution` carries optional observed quantity, price, execution time, and
source event ID. These fields allow future idempotency and event lineage work
without making the identity value object responsible for that logic.

## Partial execution model

### Full single-fill entry

One `OrderIdentity`, one `DealIdentity(role=ENTRY)`, and one
`PositionIdentity` can be represented in one lineage.

### Multi-fill entry

One order and one position can contain multiple entry `DealExecution` values,
each with its own deal identity and quantity. No aggregation is performed by
the identity model.

### Full single-deal close

One exit deal observation references the position and carries the observed
close quantity/price when available.

### Multi-deal partial close

Multiple exit observations reference the same position. Their quantities remain
separate so a reconciliation layer can determine cumulative closure.

### Duplicate and out-of-order events

The same typed deal observation may appear more than once in a lineage, and
observations may be supplied in arrival order rather than execution-time order.
The identity model preserves both facts. Idempotency and event ordering are
future reconciliation responsibilities.

## Legacy compatibility mapping

| Legacy field/value | Classification | Safe canonical mapping |
|---|---|---|
| `trades.id` / `lastrowid` | Local database identity | `TradeRecordId` only |
| `trades.ticket` | Ambiguous legacy identity | `LegacyTicketValue` only |
| `result.order` | MT5 order identity | `OrderIdentity` only when account scope is independently known |
| `positions_get()[].ticket` | MT5 position identity | `PositionIdentity` only when account scope is independently known |
| `deal.ticket` | MT5 deal identity | `DealIdentity` only when role/account scope are known |
| `deal.position_id` | Position reference carried by deal | Position reference; not an exit-deal identity |

No automatic mapping is implemented. In particular:

```text
legacy ticket -> PositionIdentity
legacy ticket -> OrderIdentity
legacy ticket -> DealIdentity
```

are all prohibited without operation-specific evidence.

## Account isolation

The repository does not establish global uniqueness for numeric MT5 tickets.
The canonical identity key must therefore include account scope and identity
type.

Required isolation cases:

1. Account A + order 123;
2. Account B + order 123;
3. Account A + position 123;
4. Account A + deal 123;
5. Account B + position 123;
6. the same numeric value used simultaneously across types.

The value model rejects cross-account lineage composition and keeps all six
cases distinct.

## Account-scoped exit boundary

The current `log_trade_exit(ticket=...)` is insufficient as a canonical
execution API because it does not carry account scope, typed position identity,
deal identity, source event identity, execution quantity, or explicit event
type.

A future typed close/reconciliation operation should be designed around:

- explicit `AccountScope`;
- `PositionIdentity`;
- optional `DealIdentity` for the closing deal;
- source event identity when supplied by the broker/evidence source;
- event timestamp;
- execution quantity and price when observed;
- explicit entry/exit event role.

This is a proposed future boundary, not a change to the legacy logger.

## Reconciliation boundary

Reconciliation should consume:

- observed MT5/broker events;
- typed account/order/position/deal identities;
- local `TradeRecordId` references when available;
- event timestamps, quantities, prices, and source IDs;
- current compatibility record state.

It should produce:

- matched/unmatched status;
- identity and account mismatches;
- missing local record or missing broker event state;
- duplicate/idempotency decisions;
- partial-fill and partial-close aggregates;
- an auditable reconciliation result.

None of these decisions belongs in the identity value objects.

## Lifecycle information required later

Phase 12 does not define transactions or concurrency. It identifies the
information required for later lifecycle work:

- stable account scope;
- typed event identity;
- source event ID for idempotency;
- event time and observed time;
- local record reference;
- incomplete-event representation;
- lineage state that survives restart;
- explicit duplicate and out-of-order handling.

## Unresolved questions

1. Are MT5 order, position, and deal numeric namespaces guaranteed unique only
   per account, or per account/server combination?
2. Does the live broker path consistently return a position ticket, or does the
   order-ticket fallback occur in production?
3. How are partial fills and partial closes currently persisted, if at all?
4. Can a position be recreated or hedged with multiple position identifiers for
   one strategy trade?
5. Which account field is authoritative for each deployed environment?
6. What source event identifier is stable across broker retries/restarts?
7. How should missing local records be linked without inventing a record ID?
8. What event ordering and idempotency guarantees does the broker history API
   provide?

## Phase 12 conclusion

The proposed value model establishes explicit account scope and distinct order,
position, deal, local-record, and legacy-ticket types. It represents partial
and incomplete lineage without performing reconciliation or changing legacy
behavior.

Production identity mapping, account-scoped exits, persistence changes, and
reconciliation remain unauthorized until the unresolved questions are answered
and a later phase is explicitly approved.
