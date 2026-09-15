# Phase 8B — Persistence Boundary Contract Design

Status: design and characterization only. No adapter, contract implementation, caller, schema, launcher, database, cache, broker, or MT5 code was changed.

## Evidence boundary

This design is based on:

- `docs/characterization/phase8_persistence_boundary.md`
- `packages/compatibility/canonical_trade_logger_contract.py`
- `packages/compatibility/legacy_trade_logger_shadow.py`
- `risk/trade_logger.py`
- Phase 6–8A characterization tests
- source inspection of direct SQL consumers

The production `trades.db` was not opened. Extended columns mentioned by newer consumers are treated as source-level expectations, not as verified properties of the deployed legacy database.

## Identity model

These identities are different and must never be conflated.

| Identity | Produced by | Legacy storage/use | Consumers |
|---|---|---|---|
| Database record ID | SQLite `AUTOINCREMENT` on entry | `trades.id`; returned by `log_trade_entry` | Qualification and tooling use `WHERE id = ?`. |
| Legacy broker-identifier ticket | Broker result passed to logger | `trades.ticket`; used by legacy exit and orphan lookup | `auto_trader_exness.py`, `TradeLogger.log_trade_exit`, orphan tools. |
| MT5 position identifier | MT5 position/reconciliation code | Newer `mt5_position_id`/`mt5_position_ticket` expectations | Qualification, metrics, integrity, normalized/V2 designs. Not written by legacy `TradeLogger`. |
| MT5 deal ticket | MT5 history-deal processing | Newer entry/exit deal fields | Reconciliation and V2/normalized designs. Not part of the legacy logger API. |

Observed compatibility rules:

- The Phase 7 entry return value is a database record identifier, not a broker ticket.
- Legacy `ticket` is nullable, indexed, and non-unique.
- Duplicate tickets are possible. Exit selects one open row for `pnl_percent`, then updates every row with that ticket.
- Legacy exit matching is not scoped by database ID, account, position, or deal.
- No current evidence supports treating `ticket`, `mt5_position_id`, order ticket, deal ticket, and `id` as aliases.

The legacy `ticket` value is ambiguous. `ai-service/broker_exness.py` may return
the MT5 position ticket when a position is found; otherwise it may fall back to
`result.order`, which is an order ticket. The close path in
`ai-service/auto_trader_exness.py` later uses `deal.position_id` as the ticket
passed to `log_trade_exit`. Therefore, `trades.ticket` is a legacy
broker-identifier field whose value may represent an order ticket or a position
ticket depending on the execution path. It must not be treated as a universally
typed order-ticket field.

The existing typed identity evidence is in
`packages/execution/mt5_identity.py`. That model distinguishes order,
position, entry-deal, and exit-deal identities; Phase 8B does not modify or
implement that model.

## Account identity

| Field | Observed role | Compatibility treatment |
|---|---|---|
| `account` | Optional legacy logger value and query filter | Preserve as-is. It may be absent because the production entry call does not pass it. |
| `account_name` | Used by integrity checks and newer consumers | Not part of the legacy logger schema or entry signature. Do not backfill from `account` in a compatibility layer. |
| `account_id` | MT5 login identity in newer execution/domain/schema code | Distinct from both names. No legacy logger persistence semantics established. |
| `environment` | Context such as live/demo/validation in newer schemas and filters | Not part of the legacy logger API. No inferred default is allowed. |

The current compatibility layer therefore does not normalize, alias, or require these fields. Account-scoped behavior must be explicitly added only after a separate approved migration contract exists. In particular, legacy exit updates are not account-scoped.

## Trade execution state

### Verified legacy fields

- `entry`, `stop_loss`, `take_profit`: signal/planned values written at entry.
- `exit_price`, `exit_time`: closure values written by legacy exit.
- `volume`: entry value passed to the logger.
- `pnl`, `pnl_percent`, `result`, `reason`: exit/performance state.
- `timestamp`: naive `datetime.now().isoformat()` entry timestamp.

### Source-level fields expected by newer consumers

`planned_entry`, `planned_sl`, `planned_tp`, `signal_entry`, `actual_entry`, `actual_sl`, `actual_tp`, `actual_exit`, `entry_deviation_pips`, `slippage_pips`, `signal_age_ms`, `spread_at_execution`, `risk_budget_usd`, `actual_risk_usd`, `mt5_closure_state`, and `execution_contract_valid` are referenced elsewhere, but are not produced by the legacy logger migration or entry INSERT. They must remain separate from the legacy fields until a compatibility projection is characterized.

No Phase 8B contract maps `entry` to `actual_entry`, or `stop_loss`/`take_profit` to actual broker protection values.

Newer execution/evidence sources also contain `actual_entry_price`,
`actual_exit_price`, `actual_volume`, MT5 profit, commission, and swap. These
are newer execution/evidence fields. They must not be mapped automatically
onto legacy `entry`, `exit_price`, or `volume`, and no schema normalization is
defined here.

## Direct SQL consumer classification

### Operational reads

- `ai-service/auto_trader_exness.py` consumes the eight `TradeLogger` methods for allocation, Monte Carlo, drift, closure logging, and daily statistics.
- `packages/execution/orphan_detector.py` checks `trades.ticket` against broker positions and reads database IDs.
- `packages/execution/final_qualification_engine.py` retrieves a row by `trades.id` and maps `SELECT *` using cursor column descriptions.

### Dashboard and reporting

- `ai-service/v3_api.py`
- `ai-service/v3_dashboard_api.py`
- `backend/services/dashboard_service.py`
- `tools/dashboard_data.py`
- `tools/v3_frontend_data.py`
- `tools/v3_daily_report.py`

These depend on strategy/account/result filters, confidence and PnL aggregates, institutional grouping, and sometimes direct `ORDER BY`/date semantics. Their output shapes are not one common repository return shape.

### Health and observability

- `packages/observability/metrics.py`
- `packages/observability/health_monitor.py`
- `packages/integrity/database/health.py`
- `packages/integrity/database/deep_health.py`
- `packages/observability/reconciliation_daemon.py`

These use `sqlite_master`, `PRAGMA table_info`, duplicate-ticket grouping, timestamp comparisons, account checks, execution evidence, closure fields, and direct aggregate SQL. Some health functions also access MT5; those side effects are outside this contract design.

### Qualification and evidence

`packages/execution/final_qualification_engine.py` and the evidence/qualification tools depend on `id`, `SELECT *`, cursor-derived column order, signal-age, actual-price, risk, position, and execution-contract fields. These consumers require a stable read projection, but the repository does not establish a stable typed row shape yet.

### Research, validation, and archive

The `tools/` and `archive/` inventories in the Phase 8A document contain direct readers and writers for historical analysis, tagging, reconciliation, repair, and reports. They use raw SQL, SQLite date functions, `ORDER BY id`, `GROUP BY`, `LIKE`, `PRAGMA`, and direct updates. They are not safe inputs to a generic production repository contract without individual migration characterization.

### SQL coupling that must remain explicit

Direct consumers depend on:

- `SELECT * FROM trades` and cursor-description column mapping;
- `PRAGMA table_info(trades)` and `sqlite_master` table inspection;
- `date(timestamp)` and `datetime('now')` SQLite functions;
- lexical comparisons of TEXT timestamps;
- `ORDER BY id`, `ORDER BY exit_time DESC`, and `LIMIT` behavior;
- `GROUP BY`, `CASE`, `COALESCE`, `ROUND`, `LIKE`, and null behavior;
- direct updates by `id` and broad updates by `ticket`.

These are read/projection and schema-compatibility concerns, not responsibilities of a trade-write façade.

## Legacy write semantics that contracts must preserve

The following are observed behavior, not proposed improvements:

1. `log_trade_entry` accepts the legacy signal plus optional volume, ticket, regime, and account.
2. It returns SQLite `cursor.lastrowid`, the database record ID.
3. It commits each successful entry.
4. `log_trade_exit` matches by ticket and open status only for its initial lookup, then updates all rows with that ticket.
5. Missing-ticket exit is a silent no-op.
6. Successful exit commits its update.
7. Exit computes `pnl_percent` as `(pnl / entry) * 100` using the first selected row.
8. Query errors propagate.
9. Exit database errors are caught and reported through the legacy warning print path.
10. The connection uses `check_same_thread=False`; the connection and cursor are public attributes. Connection ownership, connection closing behavior, and concurrent access are observed legacy behaviors, but there is currently no defined lifecycle or concurrency contract.
11. Startup creates the base table, attempts additive optional-column migrations, swallows migration exceptions, creates indexes, and commits.

## Minimum contract decomposition

### A. `CanonicalTradeLoggerContract` — retain unchanged

The Phase 7 eight-method façade remains exactly as defined:

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

Responsibility:

- preserve current callers, arguments, return shapes, commits, and legacy quirks;
- provide a compatibility façade only.

It deliberately does not own:

- broker/position/deal identity resolution;
- account normalization;
- direct row projections;
- dashboard query composition;
- schema migration policy;
- concurrency redesign.

### B. `CanonicalTradePersistenceContract` — design only, not implemented

This is the smallest persistence-level write/state boundary supported by current evidence. Its operations intentionally mirror the proven legacy operations rather than introducing new semantics:

```text
log_trade_entry(signal, volume=None, ticket=None, regime=None, account=None) -> int
log_trade_exit(ticket, exit_price, exit_time, pnl, reason="") -> None
```

Responsibility:

- persist the legacy entry and exit state;
- return the database record ID from entry;
- preserve ticket matching, duplicate-ticket, missing-ticket, commit, and error behavior during compatibility migration.

It deliberately does not own:

- a uniqueness guarantee for tickets;
- account-scoped exit semantics;
- actual MT5 execution capture;
- planned-vs-actual normalization;
- analytics queries;
- schema inspection or migration reporting.

This boundary may initially be implemented by delegation to `TradeLogger`; no adapter is created in Phase 8B.

### C. `CanonicalExecutionIdentityContract` — required as a separate future boundary

The repository evidence justifies a separate identity/reconciliation boundary because order tickets, position identifiers, deal tickets, and database IDs are consumed by different components.

The execution-identity boundary defines no persistence lookup method in Phase
8B. It remains responsible for typed order identity, position identity, entry
deal identity, exit deal identity, and reconciliation lineage. The existing
`TradeIdentity` model in `packages/execution/mt5_identity.py` is the repository
evidence for that typed distinction, but it is not modified or adopted as a
new persistence API here.

The ambiguous legacy-ticket lookup belongs to the read/projection compatibility
boundary below. It must not be presented as a canonical typed execution-
identity API.

Responsibility:

- preserve identity distinctions;
- expose explicit mappings only after their source and scope are known;
- support reconciliation without treating broker identity as database identity.

It deliberately does not own:

- order submission or MT5 access;
- trade strategy/risk decisions;
- legacy logger exit behavior;
- dashboard analytics.

### D. `CanonicalTradeReadProjectionContract` — required as a separate future boundary

Direct SQL consumers require read projections, but their shapes differ. The only currently evidenced projection signatures are:

```text
get_trade_by_record_id(record_id: int) -> mapping[str, Any]
find_record_ids_by_legacy_ticket(ticket: int) -> sequence[int]
```

`get_trade_by_record_id` is only a proposed qualification/evidence projection.
It is not a universal replacement for direct SQL or `SELECT *` consumers.
Existing consumers may depend on `cursor.description`, tuples, `SELECT *`
column order, dynamically selected columns, and direct SQLite SQL semantics.
Any future projection must preserve those compatibility requirements deliberately
for each consumer rather than assuming one universal mapping shape.

`find_record_ids_by_legacy_ticket` preserves legacy lookup without claiming
that the value is an order ticket, a position ticket, or a unique identifier.
The sequence is intentional because duplicate legacy tickets are possible.

Dashboard, analytics, health, and qualification projections must remain separate named read models later. No generic `execute(sql)` repository interface is proposed.

Responsibility:

- provide explicit, read-only compatibility views for direct consumers;
- preserve filtering, ordering, null, aggregation, and timestamp semantics during migration;
- isolate SQLite row shape from future callers.

It deliberately does not own:

- writes or transactions;
- MT5/broker calls;
- schema mutation;
- strategy or risk calculations.

### E. Schema/migration lifecycle — defer as a separate contract

A separate lifecycle contract is not justified yet. The current evidence shows that lifecycle is an implementation concern of `TradeLogger` and health tooling, with unsafe-to-generalize partial migration behavior. A future adapter will need an injected connection/path and an explicit initialization policy, but no safe public method signature is established in this phase. The legacy connection ownership, closing behavior, `check_same_thread=False` setting, and lack of a concurrency protocol must remain distinguished from any future adapter lifecycle or concurrency behavior.

Until then:

- do not expose `PRAGMA` or raw schema objects as canonical APIs;
- do not promise complete migrations;
- preserve legacy additive migration and swallowed-error behavior only inside a compatibility backend;
- characterize a lifecycle contract separately before production wiring.

## Error and transaction semantics

| Boundary | Errors | Transactions |
|---|---|---|
| Phase 7 logger façade | Query failures propagate; exit DB failures use legacy warning print; missing exit is no-op | Entry and successful exit commit independently. |
| Trade persistence | Must preserve the same behavior while compatibility mode exists | No new caller-controlled transaction scope is introduced. |
| Execution identity | No behavior established yet | Read-only until separately approved. |
| Read projections | Query errors should remain observable; no silent normalization | Read-only; no commit responsibility. |
| Schema lifecycle | Deferred | Backend-owned until characterized. |

## Migration implications

1. Keep the Phase 7 façade and legacy implementation untouched.
2. Build a shadow persistence boundary by delegation only.
3. Characterize record-ID and duplicate-ticket projections before exposing them to new callers.
4. Migrate direct SQL consumers by consumer family, beginning with read-only qualification/evidence projections.
5. Characterize account scope and planned-vs-actual fields before writing them through a new backend.
6. Do not migrate schema lifecycle or production startup until all required projections have parity evidence.

## Remaining blockers

- The deployed schema and extended-column affinities remain intentionally unverified.
- Direct consumers do not share one stable row shape.
- Account scope for identity lookup is not consistently defined.
- Position/deal persistence semantics are not implemented by the legacy logger.
- Connection ownership, closing behavior, and concurrency remain observed legacy behaviors without a defined contract.
