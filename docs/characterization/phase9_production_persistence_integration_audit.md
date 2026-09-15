# Phase 9 Production Persistence Integration Audit

## Scope and safety boundary

This document is a read-only design audit for a possible future production
persistence integration. It does not authorize or implement production wiring.

The following remain unchanged and out of scope:

- the legacy `TradeLogger` implementation;
- the Phase 7 eight-method compatibility contract;
- the Phase 8C shadow adapter;
- trading, risk, execution, broker, MT5, account-selection, and launcher code;
- the production SQLite schema and runtime database;
- caches, runtime configuration, and dashboard/API behavior.

The Phase 8C two-method adapter is a characterization boundary only. It is not
a production replacement for `TradeLogger`.

## Production seam

`ai-service/auto_trader_exness.py` constructs one `TradeLogger` and passes it
into each `AccountState`. `AccountState` stores the logger as `self.logger`.
The same logger is therefore used by both write and query operations.

Observed production-path usage is:

| Method | Current use | Operational role |
|---|---|---|
| `log_trade_entry` | `auto_trader_exness.py` after an accepted broker result | Entry persistence; the returned record ID is not used by this caller. |
| `log_trade_exit` | `auto_trader_exness.py` after MT5 close-deal discovery | Exit persistence by legacy ticket. |
| `get_recent_pnls` | Auto-trader Monte Carlo/risk monitoring | Analytics consumed during runtime. |
| `get_recent_trade_stats` | Auto-trader drift monitoring | Account-filtered analytics query. |
| `get_regime_performance` | Risk-allocation update | Regime analytics consumed during runtime. |
| `get_pair_performance` | Pair-allocation update | Pair analytics consumed during runtime. |
| `get_daily_stats` | Daily status/reporting path | Runtime operational statistics. |
| `get_performance_stats` | Public logger summary path; no separate live caller was identified | Aggregate reporting. |

The smallest eventual seam is dependency composition at the logger injected
into `AccountState`, but it must preserve the complete eight-method surface.
Replacing only the two write calls would leave the same object responsible for
runtime analytics and would not be a behavior-preserving substitution.

### Eight-method compatibility requirements

The Phase 7 contract remains unchanged:

```text
log_trade_entry(signal, volume=None, ticket=None, regime=None, account=None) -> int
log_trade_exit(ticket, exit_price, exit_time, pnl, reason="") -> None
get_recent_pnls(limit=100) -> list[float]
get_recent_trade_stats(days=30, account=None) -> tuple[int, int, float]
get_regime_performance(days=30) -> mapping
get_pair_performance(days=30) -> mapping
get_daily_stats(date=None) -> mapping | None
get_performance_stats() -> mapping
```

Observed compatibility requirements include:

- entry returns SQLite `cursor.lastrowid`;
- entry and successful exit commit independently;
- query failures propagate;
- exit database failures are caught and reported through the legacy warning
  path;
- missing-ticket exits are silent no-ops;
- legacy ticket matching and duplicate-ticket behavior remain unchanged;
- the optional `account` query filter is preserved without implying that all
  writes contain account identity.

### Why Phase 8C cannot replace `TradeLogger`

`ShadowCanonicalTradePersistenceAdapter` exposes only `log_trade_entry` and
`log_trade_exit`, intentionally. It does not provide the six query methods,
direct SQL compatibility, schema lifecycle, or production connection
ownership. Treating it as the injected production logger would remove methods
used by the auto-trader and would change the dependency surface.

## Identity findings

The following identities must remain distinct:

| Identity | Observed producer | Storage/consumer evidence | Status |
|---|---|---|---|
| SQLite trade record ID (`trades.id`) | SQLite `INTEGER PRIMARY KEY AUTOINCREMENT`; returned through `lastrowid` | Used by direct SQL synchronization and qualification queries | Safe only as database-record identity. |
| Legacy `trades.ticket` | Entry receives the broker result-derived value; exit receives `deal.position_id` from the auto-trader close path | Legacy exit lookup/update and direct SQL ticket queries | Ambiguous and untyped. |
| MT5 order ticket | `result.order` from the MT5 order result | Typed execution model and newer evidence paths | Not safely mapped to legacy `ticket`. |
| MT5 position ticket/identifier | Position lookup or `deal.position_id` | Position management, reconciliation, and typed execution model | Not safely mapped to legacy `ticket`. |
| MT5 entry deal ticket | MT5 history deal with entry/open direction | `TradeIdentity.mt5_entry_deal_ticket` and newer evidence | Separate typed identity; legacy logger does not persist it. |
| MT5 exit deal ticket | MT5 history deal with exit/close direction | `TradeIdentity.mt5_exit_deal_ticket` and newer evidence | Separate typed identity; legacy logger does not persist it. |

### Observed lineage

The legacy entry path can receive a broker-returned `ticket`. The broker code
may use a found position ticket, or fall back to `result.order`. The legacy
logger stores that value in one `ticket` column.

The close path independently discovers an MT5 exit deal and passes
`deal.position_id` to `log_trade_exit`. The legacy logger then performs a
ticket-based lookup and broad ticket-based update.

This is observed source behavior, not a safe identity mapping. The repository
does not establish a universal relation among the SQLite record ID, legacy
ticket, order ticket, position ticket, entry-deal ticket, and exit-deal ticket.

### Unknown or unsafe lineage

- There is no legacy persistence field that unambiguously stores each MT5
  identity type.
- Duplicate legacy tickets are legal at the logger boundary.
- A position ticket and an order ticket can therefore be represented by the
  same legacy column in different execution paths.
- The Phase 8C adapter forwards this value and does not create aliases.
- No future production adapter may infer identity type from the integer alone.

## Account findings

Observed account concepts are separate:

- `account`: optional legacy logger field passed to entry logging;
- `account_name`: newer consumer/schema concept such as `Live_Micro` or
  `Demo2`;
- `account_id`/login: numeric MT5 account identity in newer execution models
  and account configuration;
- environment/server: broker or MT5 deployment identity used by newer account
  context code.

The auto-trader stores account configuration in `AccountState` and has a
broker login, but its production entry call does not consistently pass the
account name into `TradeLogger.log_trade_entry`. The legacy exit signature has
no account argument and matches only by ticket.

Consequences:

- account-scoped exit matching is not an observed legacy behavior;
- adding account filtering to exits would be a behavior change;
- `account`, `account_name`, numeric login, and environment/server must not be
  normalized during persistence integration;
- newer health and evidence consumers expecting both account fields cannot be
  treated as proof that legacy writes populate both fields.

The risk is especially material because one logger is shared across account
states while legacy ticket exits are not account-scoped.

## Execution-state findings

### Planned fields observed in the legacy logger

- `entry`: signal/planned entry;
- `stop_loss`: signal/planned stop loss;
- `take_profit`: signal/planned take profit;
- `volume`: requested/logged volume;
- `timestamp`: legacy entry timestamp.

### Requested fields

The requested broker order is produced by the execution path, but the legacy
logger receives only the value selected as `ticket`, plus the signal and volume
arguments. It does not establish a distinct requested-order identity record.

### Actual fields observed in legacy persistence

- `exit_price`;
- `exit_time`;
- `pnl`;
- `pnl_percent`;
- `result`;
- `reason`.

The legacy logger does not independently persist actual entry price, actual
SL/TP, or actual volume.

### Derived fields

`pnl_percent` is derived by legacy code as `(pnl / entry) * 100` using the
first open row found by ticket. It is not an MT5 execution-performance field.

### Reconciliation/evidence fields

Newer consumers and schema experiments refer to fields including:

- `actual_entry`, `actual_exit`, `actual_sl`, `actual_tp`;
- `actual_volume`;
- `mt5_position_id`;
- `mt5_profit`, commission, and swap;
- `entry_deviation_pips`;
- `risk_budget_usd` and actual risk;
- `execution_contract_valid`;
- closure and reconciliation state.

These are newer execution/evidence concepts. They must not be silently mapped
onto legacy `entry`, `stop_loss`, `take_profit`, `volume`, or `pnl` fields.

## Direct SQL boundary

Direct SQL is a separate read/projection and operational migration problem. It
must not be hidden behind a generic `execute(sql)` repository.

### 1. Operational consumers

- `ai-service/auto_trader_exness.py` uses `TradeLogger` queries and writes.
- `ai-service/sync_positions.py` reads open rows using `id`, `pair`, `entry`,
  `volume`, and `timestamp`, then updates rows by SQLite `id`.
- `packages/execution/orphan_detector.py` queries `id` by legacy `ticket`
  while inspecting MT5 positions.

These consumers depend on the distinction between record ID and legacy ticket.

### 2. Dashboard/reporting consumers

- `backend/services/dashboard_service.py` aggregates `pnl`, `confidence`,
  `strategy_version`, and `institutional_bias`.
- `ai-service/v3_api.py` and `ai-service/v3_dashboard_api.py` aggregate
  strategy, regime, confidence, account, result, PnL, and
  `execution_contract_valid` fields.

They depend on exact SQL aggregation, NULL behavior, grouping, rounding,
strategy filters, and response shapes. A single `Mapping` projection cannot be
assumed to replace these queries.

### 3. Health and observability consumers

`packages/observability/metrics.py`, `health_monitor.py`, and
`packages/integrity/database/health.py`/`deep_health.py` use direct SQLite
connections and inspect counts, account identity, strategy metadata, open and
closed state, timestamps, duplicate tickets, risk values, MT5 position fields,
and schema columns.

These consumers use `PRAGMA table_info`, `GROUP BY`, NULL predicates, and
operational integrity assumptions. Some also perform MT5 checks, which must
remain outside a persistence write façade.

### 4. Integrity and reconciliation consumers

- `ai-service/sync_positions.py` updates by record ID after external deal
  discovery.
- `packages/observability/reconciliation_daemon.py` reads MT5 position-related
  columns.
- `packages/execution/orphan_detector.py` compares MT5 position tickets with
  legacy `trades.ticket` values.

These consumers expose the current unsafe ticket conflation and cannot be
migrated until typed identity lineage is characterized.

### 5. Qualification and evidence consumers

`packages/execution/final_qualification_engine.py` uses `SELECT *` by record ID
and expects planned/actual, risk, MT5 position, and execution-contract fields.
Its row shape is schema-sensitive and is not equivalent to the legacy logger
write contract.

### 6. Research, validation, and archive consumers

Model validation, feature analysis, analytics, and archive/tooling modules
query `trades` directly for confidence, result, PnL, timestamps, institutional
fields, and strategy/account filters. These consumers vary in row shape and
are not one production façade responsibility.

### 7. Schema experiments

`packages/persistence/schema_v2.py` and `normalized_schema.py` define or
transform newer tables and fields, including separated order, position, deal,
planned, actual, account, and reconciliation concepts. They are design or
migration experiments, not evidence that those semantics are safely present in
the legacy production schema. They must not be executed during this phase.

### SQL coupling summary

Important observed coupling includes:

- `SELECT *` and cursor/column order;
- `PRAGMA table_info` and schema existence checks;
- SQLite `date(timestamp)` behavior;
- `ORDER BY exit_time DESC` and `ORDER BY id` assumptions;
- `GROUP BY`, `CASE`, `COALESCE`, `ROUND`, and `LIKE` semantics;
- NULL versus empty-string result handling;
- broad duplicate-ticket updates;
- direct updates by record ID;
- extended columns not written by the legacy logger.

No universal read projection is approved by this audit.

## Lifecycle and transaction findings

### Observed legacy behavior

- `TradeLogger` creates its own SQLite connection in the constructor.
- It uses `check_same_thread=False`.
- It stores `conn` and `cursor` as public attributes.
- Constructor startup creates the base table, attempts additive optional-column
  migrations, swallows migration exceptions, creates indexes, and commits.
- Successful entry writes commit immediately.
- Exit performs an initial open-row lookup, then broadly updates every row with
  the matching ticket and commits.
- Query methods do not introduce a transaction abstraction and their database
  errors propagate.
- Exit database errors are caught and reported through the legacy warning-print
  path.
- Missing-ticket exits return without updating rows.
- No explicit `TradeLogger.close()` lifecycle is defined.
- Direct SQL consumers create and close their own connections inconsistently.

### Future semantics not yet defined

The repository does not establish a safe future policy for:

- connection ownership;
- cursor ownership;
- rollback scope;
- concurrent writes;
- serialization between shared logger users;
- shutdown ordering;
- complete schema migration;
- account-scoped transaction boundaries.

These must not be invented during a compatibility migration.

## Recommended future architecture

### Option D target architecture

The target should keep separate boundaries for:

1. a complete compatibility write/logger façade;
2. typed execution identity and reconciliation;
3. named read/projection contracts for direct consumers;
4. deferred schema and migration lifecycle.

The boundaries must preserve the distinction between SQLite record identity,
legacy ticket, MT5 order, MT5 position, entry deal, and exit deal.

### Option B first eventual seam

The first eventual production seam should retain the legacy `TradeLogger` as
the backend behind a complete eight-method façade. This provides a reversible
composition boundary without changing persistence behavior or introducing the
Phase 8C two-method adapter into production.

Before any wiring, that façade would require parity for all eight methods,
including return values, query shapes, account filtering, error behavior,
commits, timestamps, and duplicate-ticket semantics.

### Explicit rejection of direct Phase 8C replacement

Directly replacing `TradeLogger` with the Phase 8C adapter is rejected because
the adapter:

- implements only entry and exit;
- is explicitly shadow-only;
- accepts only isolated in-memory SQLite dependencies;
- does not provide analytics queries;
- does not provide direct SQL compatibility;
- does not provide identity mapping or reconciliation;
- does not define production lifecycle or concurrency semantics.

## Required evidence before future approvals

Before production façade implementation:

- complete source caller inventory;
- isolated parity for all eight methods;
- verified production schema characterization without migration;
- complete account identity and omission analysis;
- typed identity lineage evidence;
- direct SQL read-model inventory and row-shape characterization;
- connection, commit, exception, and concurrency characterization;
- rollback and fallback design.

Before production wiring:

- façade parity complete;
- direct SQL consumers unchanged or independently migrated;
- no unresolved identity or account-scope assumptions;
- shadow comparison evidence in a non-production environment;
- operational monitoring and rollback procedure;
- explicit approval for the exact production seam.

Before legacy retirement:

- every caller migrated;
- every direct SQL dependency addressed;
- dashboards, health, reconciliation, qualification, and validation verified;
- a controlled observation period completed;
- rollback is no longer required;
- separate approval for legacy removal.

## Phase 9 conclusion

The safe architectural direction is Option D, with Option B as the first
eventual production composition seam. Phase 8C remains frozen and shadow-only.
No production integration is authorized by this audit.
