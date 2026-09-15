# Phase 11 Production Persistence Migration Design Audit

## Executive architectural verdict

The eight-method `CanonicalTradeLoggerFacade` is a valid compatibility façade
for preserving the current `TradeLogger` API, but the surrounding persistence
architecture is not safe for production migration yet.

The blockers are structural:

1. direct SQL access is distributed across runtime, dashboard, observability,
   reconciliation, qualification, research, archive, and schema tooling;
2. `trades.ticket` conflates or ambiguously carries MT5 order and position
   identifiers;
3. exits are ticket-only and are not account-scoped;
4. connection, transaction, and concurrency semantics are implicit and
   undefined.

The façade must remain a compatibility layer, not become the identity,
reconciliation, analytics, or lifecycle boundary.

**Phase gate:** `BLOCKED — insufficient evidence` for production persistence
migration. The design can proceed, but production implementation and wiring
require additional evidence and explicit approval.

## Audit scope and safety

This audit used repository source and existing characterization artifacts only.
It did not open `trades.db`, execute migrations, connect to MT5 or a broker,
access the network, access runtime caches/configuration, or modify production
files.

The pre-existing working-tree modification
`research/paper/V4_CANONICAL_1.0/enhanced_signal_log.jsonl` remains outside the
scope of this audit.

## A. Direct SQL consumer audit

### Classification rules

- The eight-method logger façade is a compatibility API, not a generic SQL
  repository.
- Direct SQL against `trades` is recorded separately from SQL against research,
  shadow, memory, or schema-experiment tables.
- A module-level script is classified by its source role even when it is not
  proven to be active in the current launcher.
- Archive and maintenance scripts are retained as legacy/dead consumers until
  separately verified; they must not be run as part of migration.

### 1. Production runtime and operational consumers

| File | Function/class or operation | SQL/tables and fields | R/W | Runtime status | Façade suitability | Migration risk |
|---|---|---|---|---|---|---|
| `risk/trade_logger.py` | `TradeLogger` and all eight methods | `trades`; legacy entry, exit, ticket, account, PnL, regime, pair, timestamp, and metadata fields; `PRAGMA`/`ALTER TABLE` during `_migrate` | R/W | Current persistence backend | The façade delegates here; it does not replace SQL | Critical: behavior, schema, errors, and commits are all observable |
| `ai-service/auto_trader_exness.py` | `AutoTrader.__init__`, allocation, Monte Carlo, drift, exit reconciliation, entry logging, daily summary | Indirectly all eight logger methods; also constructs `ChartGenerator` and `ReportGenerator` against `trades.db` | R/W through logger; read through analytics helpers | Current live-trading consumer | Complete eight-method façade can preserve the logger dependency; Phase 8C cannot | Critical: shared logger, account ambiguity, and live execution adjacency |
| `analytics/chart_generator.py` | `ChartGenerator.generate_equity_curve` | Reads `timestamp`, `pnl` from `trades` | R | Constructed by live auto-trader | Requires a read/projection interface, not the logger façade | High: chart rows and ordering must remain identical |
| `analytics/report_generator.py` | `ReportGenerator.generate_report` | Aggregates `pnl`, `exit_price`, `timestamp`, and entry/closed status from `trades` | R | Constructed by live auto-trader | Requires a report projection | High: dashboard/report output depends on SQL semantics |
| `ai-service/sync_positions.py` | Module-level synchronization script | Reads open rows by `id`, `pair`, `entry`, `volume`, `timestamp`; selects MT5 exit deals by symbol/time; updates `exit_price`, `exit_time`, `pnl`, `pnl_percent`, `result` by SQLite `id`; commits batch | R/W | Operational repair/reconciliation script | No; requires typed reconciliation boundary | Critical: symbol/time matching can select the wrong position |
| `ai-service/v3_api.py` | `get_dashboard_data` | Aggregates V3/PRE_V3 `trades` by strategy, PnL, confidence, institutional bias, and confidence ranges | R | API/reporting path or legacy API | Requires named dashboard read model | High: response shape and rounding are SQL-derived |
| `ai-service/v3_dashboard_api.py` | `v3_dashboard`, health/metrics endpoints | Filters `trades` by account, strategy, result, `execution_contract_valid`; aggregates regime, confidence, PnL | R | Dashboard/API path | Requires explicit V3 projection | Critical: expects newer columns not guaranteed by legacy writes |
| `backend/services/dashboard_service.py` | `get_dashboard` | Aggregates V3/PRE_V3 strategy, PnL, confidence, institutional bias | R | Backend dashboard path | Requires dashboard projection | High |
| `ai-service/daemon_v2.py` | Dashboard/report helper in legacy daemon | Direct V3/PRE_V3 strategy, PnL, confidence, institutional bias and confidence-range aggregation | R | Competing/legacy daemon implementation | No direct façade replacement | High if still launched; status must be verified |

The current auto-trader therefore has more than a write dependency. Replacing
only `log_trade_entry` and `log_trade_exit` would leave runtime analytics and
chart/report SQL behavior unresolved.

### 2. Analytics and reporting consumers

| File | Function/class | Operation and fields | Classification | Façade suitability |
|---|---|---|---|---|
| `analytics/analytics.py` | `main` | Reads closed `trades` fields `pair`, `signal`, `timestamp`, `exit_time`, `pnl`, `regime`, `confidence`; groups by session/pair/regime | Analytics | New read/query interface |
| `analytics/confidence_audit.py` | `main` | Reads `confidence`, `pnl` for closed trades and computes confidence buckets | Analytics | New read/query interface |
| `analytics/chart_generator.py` | `ChartGenerator` | Reads timestamp/PnL series | Reporting | New projection |
| `analytics/report_generator.py` | `ReportGenerator` | Counts closed trades, sums positive/negative PnL, reads timestamp/PnL series | Reporting | New projection |
| `institutional/performance_tracker.py` | `InstitutionalPerformanceTracker` | Aggregates `pnl`, `institutional_bias`, timestamps, counts, averages, and historical/current metadata | Analytics | New analytics read model |
| `institutional/research_dashboard.py` | `dashboard` | Aggregates `trades`, `trade_memory`, and `performance_memory`; directly updates open trades with `exit_price=entry`, `exit_time=timestamp`, `pnl=0`, `result='UNKNOWN'` | Reporting and operational repair | Must not use write façade for direct repair; separate approved operation |
| `institutional/learning_engine.py` | `AdaptiveLearningEngine` methods | Reads closed `trades` by pair, regime, confidence, institutional fields, and PnL | Research/analytics | New research projection |
| `institutional/data_quality_report.py` | Module-level report | Reads `trades`, `shadow_trades`, and `research_decisions`; grouping and count queries | Research/quality | Separate read interfaces |
| `institutional/evidence_package.py` | Module-level evidence report | `PRAGMA table_info(trades)` and counts of institutional/PnL fields | Evidence/schema inspection | Separate schema/evidence interface |

These consumers depend on fields and semantics beyond the Phase 7 contract.

### 3. Health and observability consumers

| File | Function/class | SQL behavior | Risk |
|---|---|---|---|
| `packages/observability/metrics.py` | `get_metrics` | Counts V3 trades, execution exceptions, missing MT5 positions, deviation, planned/actual values, open states | Expects newer schema fields and exact NULL/result semantics |
| `packages/observability/health_monitor.py` | `HealthMonitor` checks | Counts open trades without MT5 positions, timestamp ordering, account/volume/risk violations, PnL integrity; closes each connection | Direct schema and account coupling; some checks also initialize MT5 |
| `packages/observability/reconciliation_daemon.py` | `ReconciliationDaemon.check_db_vs_mt5`, orphan checks | Reads `ticket`, `mt5_position_id`, `account`, `account_name`; compares database rows with MT5 positions | Unsafe until typed identity and account scope exist |
| `packages/integrity/database/deep_health.py` | Registered DB checks | Opens the production path; checks tables, columns, duplicate tickets, timestamps, account identity, strategy, orphan state, contamination | Direct production schema assumptions; includes duplicate-ticket policy not enforced by legacy logger |
| `packages/integrity/database/health.py` | `check_database_health` | `PRAGMA integrity_check` and trade count | Separate health interface |
| `packages/integrity/mt5/deep_health.py` | MT5/database health checks | MT5 plus direct database checks | Cross-boundary; not a logger concern |
| `packages/integrity/system_integrity_gate.py` | Integrity gate checks | Direct `trades` counts and invariants | Must remain separate from write façade |

### 4. Reconciliation, qualification, and execution-evidence consumers

| File | Function/class | Operation | Façade suitability |
|---|---|---|---|
| `packages/execution/orphan_detector.py` | `detect_orphans` | Reads `trades.id` by legacy `ticket` while comparing MT5 positions | Requires typed identity/reconciliation; cannot use ticket alias |
| `packages/execution/final_qualification_engine.py` | `print_final_qualification` | `SELECT * FROM trades WHERE id=?`; expects actual prices, risk, MT5 position, and execution-contract fields | Requires an explicit evidence projection preserving row shape |
| `packages/strategy/model_validation.py` | `get_v3_trades_for_validation` | Reads `confidence`, `result`, `strategy_version`, `account`, `execution_contract_valid` | Research projection; not logger façade |
| `ai-service/sync_positions.py` | Module-level reconciliation | Matches by pair/time and updates by record ID | Requires redesign of lineage before migration |
| `packages/execution/mt5_reconciler.py` | `resolve_trade_identity`, `reconcile_db_with_mt5` | Queries MT5 deals by position ticket and compares price, volume, PnL | MT5 identity/reconciliation boundary, not persistence façade |

### 5. Research, validation, shadow, and memory tables

The following modules access SQLite but not necessarily the legacy `trades`
table. Their tables are separate persistence domains and must not be forced
through the eight-method trade logger façade:

| Files | Tables | Operations | Classification |
|---|---|---|---|
| `institutional/strategy_memory.py`, `institutional/performance_intelligence.py` | `strategy_memory`, `trade_memory`, `performance_memory` | Create/read/update/insert aggregate memory rows | Research/learning persistence |
| `institutional/historical_replay_engine.py`, `institutional/shadow_simulator.py`, `institutional/shadow_collector.py` | `shadow_trades`, `opportunity_stats`, related shadow tables | Insert/update/read simulated outcomes and opportunity statistics | Research/shadow persistence |
| `institutional/shadow_executor.py` | `shadow_executions` | Insert simulated executions and aggregate results | Research/shadow persistence |
| `institutional/research_collector.py`, `institutional/outcome_tracker.py` | `research_decisions` | Insert decisions, update outcomes, aggregate grades | Research evidence persistence |
| `institutional/research_dashboard.py` | `trade_memory`, `performance_memory`, `trades` | Dashboard reads plus direct open-trade repair | Mixed reporting/repair |
| `ai-service/show_history.py` | `historical_summary`, `trades` | Aggregate historical/trade counts | Legacy reporting |
| `ai-service/check_memory.py`, `ai-service/sync_memory.py` | `trade_memory` and/or `trades` | Memory checks/synchronization | Legacy/research tooling |

These require separate named contracts if they remain in scope. They are not
methods to add to `CanonicalTradeLoggerContract`.

### 6. Migration and schema tooling

| File/group | Operation | Classification | Production status |
|---|---|---|---|
| `packages/persistence/schema_v2.py` | Creates `trades_v2`, migrates from `trades`, reads validated/phantom rows | Schema experiment/migration | Must not run without separate approval |
| `packages/persistence/normalized_schema.py` | Creates signals/orders/positions/deals/trades_normalized tables | Schema experiment | Must not run without separate approval |
| `tools/add_account_filtering.py` | Adds or updates account-related schema/data | Migration tooling | Legacy/destructive risk |
| `tools/add_execution_fields.py` | Adds execution fields | Migration tooling | Legacy/destructive risk |
| `tools/add_planned_columns.py` | Adds planned fields | Migration tooling | Legacy/destructive risk |
| `tools/add_version_column.py` | Adds strategy version | Migration tooling | Legacy/destructive risk |
| `tools/complete_evidence_columns.py` | Adds/completes evidence fields | Migration tooling | Legacy/destructive risk |
| `tools/create_execution_ledger.py` | Creates execution ledger structures | Migration/tooling | Candidate future evidence only; not approved |
| `tools/fix_execution_capture.py`, `tools/fix_execution_contract.py` | Updates execution evidence | Repair/migration tooling | Must not run |
| `tools/fix_trade_logger.py`, `tools/fix_trade_states.py`, `tools/fix_v3_metadata.py` | Mutates legacy trade rows or logger-related state | Repair tooling | Must not run |
| `tools/fix_closed_pnl.py`, `tools/fix_closure_and_risk_evidence.py`, `tools/fix_remaining_closed.py` | Repairs exit/PnL/evidence fields | Repair tooling | Must not run |
| `tools/fix_id*.py`, `tools/sync_id*.py`, `tools/reconcile*.py`, `tools/sync_mt5*.py`, `tools/sync_orphan_position.py` | Direct repair/reconciliation by IDs, tickets, timestamps, or MT5 state | Repair/reconciliation tooling | Must not run |

The full maintenance set also includes `tools/audit_*.py`, `tools/check_*.py`,
`tools/diagnostics.py`, `tools/evidence_based_audit.py`,
`tools/qualified_trade_*.py`, `tools/trade_qualification.py`,
`tools/trade_summary.py`, `tools/v3_*.py`, `tools/verify_*.py`,
`tools/today_stats.py`, and `tools/yesterday_stats.py`. These are direct
read/repair consumers and must be classified individually before any
production schema change.

### 7. Tests and characterization

The following intentionally use isolated or mocked persistence:

- `tests/characterization/test_phase5_trade_logger_parity.py`;
- `test_phase6_trade_logger_shadow_parity.py`;
- `test_phase7_canonical_trade_logger_parity.py`;
- `test_phase8_persistence_boundary_characterization.py`;
- `test_phase8b_persistence_boundary_contracts.py`;
- `test_phase8c_shadow_persistence_adapter.py`;
- `test_phase9_production_persistence_integration_boundaries.py`;
- `test_phase10_eight_method_production_facade.py`;
- `test_legacy_v3_execution.py` and related characterization fixtures.

These are evidence sources, not production consumers. Their use of
`SQLite :memory:` must remain isolated.

### Direct SQL conclusion

The eight-method façade cannot replace direct SQL consumers. A future migration
needs at least:

1. a compatibility write/logger API;
2. named read projections for dashboard/reporting and runtime analytics;
3. a typed execution identity/reconciliation boundary;
4. separate research/shadow/memory persistence interfaces;
5. a separately approved lifecycle/schema boundary.

No generic `execute(sql)` abstraction is recommended.

## B. MT5 and ticket identity audit

### Identity-flow table

| Source | Identifier | Meaning | Stored location | Consumer | Ambiguity/risk |
|---|---|---|---|---|---|
| SQLite `INSERT` | `trades.id` / `lastrowid` | Database record identity | `trades.id` | `sync_positions.py`, qualification, direct SQL | Not an MT5 identity; safe only within the database |
| `MT5Broker.place_market_order` | `result.order` | MT5 order ticket | May fall back into legacy `trades.ticket` | Broker result path | Can be confused with a position ticket |
| `MT5Broker.place_market_order` | `positions_get().ticket` | MT5 position ticket | May be stored in legacy `trades.ticket` | Entry logging, position management | Selected as the maximum symbol position; not guaranteed to be the newly opened position |
| `auto_trader_exness.py` position snapshot | `position['ticket']` | MT5 position ticket | In in-memory `previous_tickets`/current sets | Detects newly closed positions | Account/session state is external to the legacy ticket |
| MT5 close history | `deal.position_id` | Position identifier associated with an exit deal | Passed to legacy `log_trade_exit` as `ticket` | Exit logging | It is not the exit deal ticket itself |
| MT5 history deal | `deal.ticket` | MT5 deal ticket | Typed `TradeIdentity` only in newer model | Reconciliation/evidence | Legacy logger has no dedicated deal field |
| `packages/execution/mt5_identity.py` | `mt5_order_ticket` | Explicit order identity | `TradeIdentity` model | Typed execution/reconciliation code | Not connected to legacy `TradeLogger` |
| `packages/execution/mt5_identity.py` | `mt5_position_ticket` | Explicit position identity | `TradeIdentity` model | Typed execution/reconciliation code | Not connected to legacy `TradeLogger` |
| `packages/execution/mt5_identity.py` | entry/exit deal tickets | Explicit deal identities | `TradeIdentity` model | Reconciliation/evidence | Not connected to legacy `TradeLogger` |

### Current legacy ticket meaning

The broker implementation submits a pending order and, after success, checks
positions for the symbol. If positions exist it returns the maximum position
ticket; otherwise it returns `result.order`. `auto_trader_exness.py` stores the
returned value in `trades.ticket`.

The close path discovers a deal with `deal.entry == 1`, takes
`deal.position_id`, and passes that value as the legacy `ticket` to
`log_trade_exit`.

Therefore the same column can contain an order ticket or position ticket. It
does not contain a consistently typed deal ticket, and it is not the SQLite
record ID.

### Reconciliation limitations

`packages/execution/mt5_reconciler.py` has a safer position-scoped lineage
model: it queries deals by position ticket and distinguishes entry and exit
deals. That model is not integrated with legacy persistence.

`ai-service/sync_positions.py` is less safe: it selects open database rows and
matches MT5 exit deals by symbol and nearest timestamp, then updates by
database record ID. It does not use a typed position-to-trade mapping.

The current `trades.ticket` field cannot safely represent the identity required
for production reconciliation.

### Minimum future identity model

The eventual model should preserve, at minimum:

1. database trade-record identity, independent of broker identity;
2. explicit account context containing account/login and server/environment;
3. order identity, scoped by account/broker;
4. position identity, scoped by account/broker;
5. deal identity with explicit entry/exit direction;
6. a lineage relation from strategy trade/record to order, position, and one or
   more deals;
7. many-to-one deal aggregation for partial fills and partial closes;
8. event/idempotency identity for repeated reconciliation observations.

Duplicate numeric ticket values across accounts must be distinguished by typed
identity plus account/broker scope. No schema change or alias is proposed in
this phase.

## C. Account-scoped exit audit

### Observed callers

Entry:

```text
acc.logger.log_trade_entry(
    signal,
    volume=lot_size,
    ticket=ticket,
    regime=regime,
)
```

The production call does not pass `account=acc.name`, even though the method
accepts the optional argument.

Exit:

```text
acc.logger.log_trade_exit(
    ticket=ticket,
    exit_price=exit_price,
    exit_time=exit_time,
    pnl=pnl,
    reason="closed",
)
```

The ticket is derived from `deal.position_id`; no account is supplied.

### Current semantics

`TradeLogger.log_trade_exit` first selects one open row by `ticket` and then
updates every row with that ticket. The update has no account predicate and no
record-ID predicate.

Duplicate tickets are legal in the legacy schema and are not rejected by the
logger.

### Failure scenario

If account A and account B contain rows with the same numeric ticket, an exit
observed for account A can update both rows. Even without numeric collision,
the current shared logger and ticket-only lookup provide no proof that the
ticket belongs to the account currently being processed.

Consequences include:

- cross-account exit timestamps and prices;
- duplicated or incorrect PnL;
- corrupted daily/account statistics;
- reconciliation false positives/negatives;
- dashboard contamination;
- incorrect risk-allocation inputs.

**Severity: critical for a multi-account production migration.**

### Recommended future contract

The future typed close/reconciliation contract should identify a position using
explicit account/broker scope plus a typed position identity, and should carry
the exit deal identity when available. A database record ID may be used as a
local persistence reference, but it must not substitute for MT5 identity.

The legacy ticket-only exit method must remain available only as a compatibility
method until all callers are migrated and parity/rollback evidence exists.

## D. Lifecycle, concurrency, and transaction audit

### Creation and ownership

`AutoTrader.__init__` creates one `TradeLogger(db_path="trades.db")`. That
single logger is passed into every `AccountState`; accounts do not receive
separate logger instances in the current production path.

The main auto-trader loop processes accounts sequentially in one process. The
repository also contains APIs, dashboards, health monitors, reconciliation
daemons, maintenance scripts, and research tools that can open the same
database independently.

### Connection and cursor

Observed legacy behavior:

- `sqlite3.connect(db_path, check_same_thread=False)`;
- public `conn` and `cursor` attributes;
- no explicit `close()` method on `TradeLogger`;
- connection initialization performs schema creation, additive migration
  attempts, index creation, and commit;
- direct consumers create their own connections with varying paths/timeouts;
- no shared connection registry or ownership protocol exists.

`check_same_thread=False` permits a connection to be used by multiple threads;
it does not provide serialization, transaction isolation policy, or safety for
concurrent cursor use.

### Transaction boundaries

- `_migrate` commits once after schema/index work.
- `log_trade_entry` inserts and commits one entry.
- `log_trade_exit` selects, computes, updates, and commits when a matching row
  exists.
- Query methods do not expose transaction scopes.
- `sync_positions.py` updates a batch and commits once at the end.
- Direct repair tools generally commit their own batch.
- There is no explicit rollback in `TradeLogger` error paths.

### Exception and crash behavior

- Entry database errors propagate; an explicit rollback is not performed.
- Exit database errors are caught and printed; callers receive `None`, and no
  structured failure is returned.
- Query errors propagate.
- A crash after broker order success but before entry commit can create a
  broker/database orphan.
- A crash or database error after MT5 close but before exit persistence can
  leave the database open while MT5 is closed.
- A batch synchronization crash can leave a partial batch applied.
- Repeated close observations can reapply broad ticket updates.

### Locking and multi-process risk

SQLite default locking can produce `database is locked` failures when runtime,
dashboard, health, reconciliation, and repair processes overlap. The legacy
logger has no busy-retry, writer serialization, or application-level lock.

No source evidence establishes whether these processes are simultaneously
active in deployment. That is an unresolved operational question, not evidence
of safety.

### Concurrency conclusion

The current lifecycle is not a production migration contract. It is an
observed implementation detail that must be characterized under isolated
thread/process doubles before any replacement backend or dependency injection.

## E. Façade architecture review

### Responsibilities the façade should retain

The eight-method façade should temporarily retain:

- legacy entry persistence;
- legacy exit persistence;
- runtime analytics methods currently consumed by `AutoTrader`;
- legacy return shapes, exceptions, commits, timestamps, account filtering,
  duplicate tickets, and missing-ticket behavior.

This is a compatibility surface, not a canonical semantic model.

### Methods that may eventually move or deprecate

The six `get_*` methods are analytics/reporting concerns. They remain on the
façade while current callers depend on them, but should eventually be replaced
by named read projections:

- `get_recent_pnls` and `get_recent_trade_stats` could move to runtime risk
  analytics;
- `get_regime_performance` and `get_pair_performance` could move to allocation
  analytics;
- `get_daily_stats` could move to an operational reporting projection;
- `get_performance_stats` is the earliest deprecation candidate because no
  direct live caller was identified, subject to complete caller inventory.

`log_trade_entry` and `log_trade_exit` should remain as compatibility wrappers
until all legacy callers are migrated. `log_trade_exit` must not be treated as
the eventual typed reconciliation API.

### Capabilities that must not be added to the façade

Do not add methods for:

- raw SQL execution;
- schema creation or migration;
- MT5 order/position/deal lookup;
- account normalization;
- position close/reconciliation;
- partial-fill aggregation;
- dashboard-specific projections;
- research-memory tables;
- transaction management without an approved lifecycle contract;
- generic repository access.

### Separate future boundaries

| Boundary | Owns | Does not own |
|---|---|---|
| Compatibility logger façade | Eight legacy methods and parity | Typed identity, raw SQL, schema, lifecycle redesign |
| Trade write/persistence boundary | Canonical persisted trade state and local record identity | MT5 identity resolution and dashboard SQL |
| Execution identity boundary | Typed order, position, entry-deal, exit-deal identities | Strategy, risk, or legacy ticket semantics |
| Reconciliation boundary | Position/deal lineage, idempotency, mismatch handling | Legacy dashboard aggregates |
| Read/projection boundary | Explicit query shapes for runtime, dashboard, health, and qualification | Writes, broker calls, schema mutation |
| Research/shadow persistence | Research decisions, shadow executions, memories | Live trade state |
| Lifecycle/transaction boundary | Connection ownership, writer serialization, rollback/recovery | Strategy and identity semantics |

## F. Target architecture options

### Option A — Thin compatibility façade over legacy `TradeLogger`

**Correctness:** preserves current behavior but preserves ticket ambiguity and
account-unsafe exits.

**Multi-account:** unsafe without changing legacy semantics.

**MT5 identity:** no improvement.

**Concurrency/transactions:** unchanged and undefined.

**Migration complexity:** lowest.

**Backward compatibility:** highest.

**Testing:** easiest using existing parity fixtures.

**Performance:** effectively unchanged.

**Maintainability:** limited; direct SQL and legacy quirks remain distributed.

**Rollback:** simple because legacy remains the backend.

**Assessment:** appropriate only as a temporary compatibility bridge, not the
target architecture.

### Option B — Canonical trade repository plus compatibility façade

The façade would preserve the eight legacy methods while a new repository
owns canonical trade writes and local record identity.

**Correctness:** potentially better, but unsafe if it attempts to infer MT5
identity or account scope during initial migration.

**Multi-account:** possible only with explicit account context and typed keys.

**MT5 identity:** still requires a separate identity/reconciliation boundary.

**Concurrency/transactions:** can be improved, but changing commit behavior is
a migration risk.

**Migration complexity:** medium to high.

**Backward compatibility:** good if the façade delegates/projections preserve
all legacy shapes.

**Testing:** requires write parity, query parity, and failure/rollback tests.

**Performance:** potentially better with controlled connections and indexes,
but not proven.

**Maintainability:** better than A if read and identity responsibilities stay
separate.

**Rollback:** possible if the façade retains the legacy backend switch.

**Assessment:** useful as an intermediate implementation direction after the
identity and lifecycle evidence exists.

### Option C — Separate execution ledger/reconciliation model plus analytics read model

The compatibility façade remains for legacy callers, while new boundaries
represent typed execution events, account scope, reconciliation lineage, and
consumer-specific read projections.

**Correctness:** strongest; preserves identity distinctions and supports
partial fills/partial closes.

**Multi-account:** explicit account/broker scope can be enforced.

**MT5 identity:** order, position, and deal identities remain separate.

**Concurrency/transactions:** can define append/reconcile transaction rules
without changing the legacy façade immediately.

**Migration complexity:** highest.

**Backward compatibility:** preserved through the façade and compatibility
projections.

**Testing:** broadest but provides the required safety evidence.

**Performance:** can use purpose-built projections, but requires operational
monitoring and indexing design.

**Maintainability:** strongest long-term separation of concerns.

**Rollback:** safe if the legacy path remains authoritative until projections
and reconciliation are verified.

**Assessment:** recommended target architecture.

### Recommendation

Choose **Option C as the target**, using **Option A as the temporary bridge**.
Option B should be introduced only after the identity, account, direct SQL,
and lifecycle gates are complete.

Option A alone is insufficient because it preserves the exact risks this audit
identified. Option B alone can still reproduce identity conflation if the
repository is designed around one `ticket` field. Option C keeps execution
identity, reconciliation, and analytics independent from the legacy API.

## G. Staged migration plan

### Phase 11 — Direct SQL inventory and design

**Objective:** complete consumer-by-consumer SQL contracts and classify active,
legacy, research, and migration tooling.

**Allowed files:** new audit/design documents and isolated characterization
tests only.

**Forbidden files:** all production callers, `TradeLogger`, schema, database,
launchers, caches, and configuration.

**Tests:** static SQL inventory, query-shape fixtures, isolated SQLite tests.

**Safety gate:** every important consumer has an owner, schema dependency,
return shape, and migration status.

**Rollback:** no runtime change; discard only unapproved design artifacts.

### Phase 12 — Canonical identity and account model design

**Objective:** define typed order/position/deal identity and explicit account
scope without mapping legacy `ticket` automatically.

**Allowed files:** new execution identity value types and isolated fixtures,
only after separate approval.

**Forbidden files:** legacy ticket writes, broker behavior, MT5 callers,
database schema, and production wiring.

**Tests:** duplicate tickets across accounts, partial fills, partial closes,
identity lineage, missing deal/order events.

**Safety gate:** no identity can be silently represented by the legacy ticket.

**Rollback:** remove only unused shadow identity artifacts; legacy path remains
unchanged.

### Phase 13 — Repository and projection boundary design

**Objective:** define separate write, identity/reconciliation, read-projection,
and lifecycle contracts.

**Allowed files:** new contract/projection artifacts and isolated adapters.

**Forbidden files:** production dependency injection, schema migration, direct
SQL replacement, and logger changes.

**Tests:** contract shape, SQL row compatibility, error and transaction
characterization.

**Safety gate:** no generic SQL repository; each interface has one bounded
responsibility.

**Rollback:** leave the legacy logger and direct SQL consumers untouched.

### Phase 14 — Expanded characterization and parity

**Objective:** prove legacy-vs-canonical behavior for writes, queries, identity
lineage, account scope, duplicate events, and lifecycle failures.

**Allowed files:** characterization tests, fixtures, and documentation.

**Forbidden files:** production runtime and database.

**Tests:** all cases in the Test Strategy section below.

**Safety gate:** no unexplained parity discrepancy remains.

**Rollback:** stop at the failing boundary and retain legacy behavior.

### Phase 15 — Offline/shadow integration

**Objective:** exercise the future composition graph with fake broker/MT5,
`:memory:` or disposable test databases, and historical replay.

**Allowed files:** shadow composition and test-only adapters.

**Forbidden files:** production launchers, live accounts, production DB,
production logs, and production cache.

**Tests:** full lifecycle replay, failure injection, duplicate/retry behavior,
read-projection parity.

**Safety gate:** no real side effects and complete output parity against the
+legacy baseline.

**Rollback:** disable shadow composition; production remains untouched.

### Phase 16 — Production dependency injection

**Objective:** only after explicit approval, introduce a reversible façade at
the logger composition seam while retaining legacy fallback.

**Allowed files:** specifically approved composition-root/caller files only.

**Forbidden files:** strategy, risk, broker, MT5, account selection, schema,
and direct SQL consumers unless separately approved.

**Tests:** canary/shadow comparison, account isolation, database-lock behavior,
rollback switch, complete regression suite.

**Safety gate:** no live cutover until production-like non-live validation and
rollback are verified.

**Rollback:** restore legacy composition immediately; no schema reversal unless
separately approved.

### Phase 17 — Legacy retirement

**Objective:** retire only unused legacy methods/modules after every consumer
has migrated and the observation period is complete.

**Allowed files:** explicitly approved deprecation/removal targets.

**Forbidden files:** deletion before caller inventory, parity, rollback, and
production evidence are complete.

**Tests:** full regression, direct-SQL consumer compatibility, reconciliation,
and restart recovery.

**Safety gate:** no remaining runtime or research dependency and an approved
rollback window has expired.

**Rollback:** retain compatibility wrappers until removal is separately
approved; do not delete during earlier phases.

## H. Test strategy

### Identity and account cases

Test with isolated fixtures for:

- one account with one order, one position, entry deal, and exit deal;
- multiple accounts with identical numeric order/position/deal values;
- order ticket different from position ticket;
- multiple entry deals for partial fills;
- multiple exit deals for partial closes;
- same symbol with multiple positions;
- duplicate legacy tickets;
- missing account context;
- account mismatch between configured context and observed MT5 identity;
- exit event supplied with position identity but no deal identity;
- exit event supplied with deal identity but no database record.

### Lifecycle and transaction cases

Test with fake connections and isolated SQLite:

- entry commit success;
- exit commit success;
- exception before insert commit;
- exception after insert but before commit;
- exception during exit lookup;
- exception during exit update;
- absent rollback behavior characterization;
- database lock and busy timeout;
- concurrent readers and writers;
- two threads sharing one logger;
- separate logger instances sharing one database;
- separate processes using the same database;
- crash/restart after broker success before entry persistence;
- crash/restart after MT5 close before exit persistence;
- repeated exit event and idempotency handling;
- partial batch synchronization failure.

### Direct SQL and projection cases

For each consumer family, test:

- exact columns and aliases;
- tuple versus mapping shape;
- `SELECT *` column order;
- `PRAGMA`/schema expectations;
- ordering by timestamp, exit time, and record ID;
- NULL and empty-string semantics;
- date functions and timezone representation;
- duplicate-ticket query behavior;
- account filters;
- aggregate rounding and zero-row behavior;
- dashboard/API response parity.

### Safety properties

Every test must prove:

- no real MT5/broker/network call;
- no production database/cache/configuration access;
- no order, position, or database write outside the isolated fixture;
- no change to strategy/risk/execution behavior;
- deterministic replay inputs and explicit treatment of dynamic timestamps.

## I. Unresolved questions

The following require evidence before production implementation:

1. What is the exact deployed `trades` schema and which newer columns are
   actually present in production?
2. Which APIs, daemons, health processes, and repair scripts are simultaneously
   active in deployment?
3. Are MT5 ticket namespaces guaranteed unique only within an account, and can
   the same numeric ticket occur across configured accounts?
4. Does `MT5Broker.place_market_order` always return a position ticket on the
   current production path, or does the `result.order` fallback occur in live
   cases?
5. How are partial fills and partial closes represented in current production
   evidence?
6. Which dashboard/API response shapes are contractual for users?
7. Which direct SQL tools are operationally authorized versus historical/dead?
8. What process/thread model actually surrounds the auto-trader and database?
9. What is the accepted behavior after a broker success followed by a database
   failure?
10. Is any existing backup/restore or journal policy relied upon operationally?
11. Which account identity fields are authoritative for each environment?
12. What is the approved rollback mechanism for a persistence composition change?

## Final recommendation

Do not migrate production persistence yet. Preserve the eight-method façade as a
compatibility surface, but build the eventual architecture around separate
typed execution identity, reconciliation lineage, read projections, and an
explicit lifecycle/transaction policy.

The current evidence supports design work only. It does not support production
dependency injection, database migration, account-scoped exit changes, or
legacy retirement.
