# Phase 8A — Persistence Boundary Gap Characterization

Status: characterization only. No production path, contract, database, cache, configuration, broker, or launcher was changed.

## Scope and evidence

This inventory is based on repository source inspection and isolated behavior tests. The production `trades.db` was not opened. The legacy write implementation is `risk/trade_logger.py`; its characterized interface remains the Phase 7 reference:

`log_trade_entry`, `log_trade_exit`, `get_recent_pnls`, `get_recent_trade_stats`, `get_regime_performance`, `get_pair_performance`, `get_daily_stats`, and `get_performance_stats`.

The repository contains more than one persistence design. `packages/persistence/schema_v2.py` and `packages/persistence/normalized_schema.py` are proposals/alternate schemas, not evidence that the legacy `trades` table has those columns. Their fields are recorded below as competing consumer/schema expectations only.

## Complete persistence boundary

### A. TradeLogger API callers

| File | Functions/operations | Methods | Important assumptions |
|---|---|---|---|
| `ai-service/auto_trader_exness.py` | `AutoTrader.__init__`, risk allocation, Monte Carlo, drift, close reconciliation, daily summary | All eight methods | Constructs `TradeLogger("trades.db")`; entry return is treated as a broker/order flow result elsewhere, while queries expect legacy tuples/dicts. Entry calls omit `account`; exit is passed a broker ticket. |
| `tests/characterization/test_phase5_trade_logger_parity.py` | Legacy characterization | All eight plus `conn`/SQL inspection | Captures schema, defaults, commit/error, timestamp, query, partial-schema, duplicate-related prerequisites. |
| `tests/characterization/test_phase6_trade_logger_shadow_parity.py` | Shadow adapter parity | All eight | Delegation must preserve return shapes and errors. |
| `tests/characterization/test_phase7_canonical_trade_logger_parity.py` | Contract parity | All eight | Defines the current backend-neutral surface; it intentionally does not define schema or connection lifecycle. |
| `tests/characterization/test_legacy_v3_execution.py` | Execution evidence | Entry plus direct SQL | Uses returned values and reads rows by `ticket`. |
| `tools/verify_next_trade.py` | Offline simulation/tooling | `log_trade_entry` | Returns a database row id, then queries `trades WHERE id = ?`; this proves record-id exposure to tooling. |
| `archive/reapply_fixes.py`, `archive/add_trade_log.py` | Historical source-edit scripts | Entry call text | Historical copies; not production callers. |

### B. Direct SQL and table consumers

Active/service-facing consumers read the legacy `trades` table directly:

| File | Operations | Main columns/assumptions |
|---|---|---|
| `ai-service/v3_api.py` | Aggregate V3/PRE_V3 dashboard queries and institutional grouping | `strategy_version`, `pnl`, `confidence`, `institutional_bias`; no account scope. |
| `ai-service/v3_dashboard_api.py` | V3 dashboard, regime and confidence aggregates, archive query | `strategy_version`, `account`, `result`, `execution_contract_valid`, `regime`, `confidence`, `pnl`; uses `SELECT` filters and ordering/aggregation in SQL. Also reads `signals_cache.json`, which is outside this phase. |
| `backend/services/dashboard_service.py` | Dashboard aggregates and confidence buckets | `strategy_version`, `pnl`, `confidence`, `institutional_bias`; also has a separate MT5 side effect in its dashboard function, not used by characterization. |
| `packages/observability/metrics.py` | Prometheus counters/gauges | `strategy_version`, `account`, `result`, `mt5_position_id`, `pnl`, `entry_deviation_pips`, `planned_entry`, `actual_entry`, `execution_contract_valid`; latest price row is `ORDER BY id DESC LIMIT 1`. |
| `packages/observability/health_monitor.py` | DB/MT5 consistency, PnL integrity, risk checks | Open-state/result, `mt5_position_id`, timestamps, `account`, `volume`, `strategy_version`, `regime`, `account_name`, `entry`, `pnl`; assumes timestamp lexical comparison and account consistency. |
| `packages/integrity/database/health.py` | Connection/readability/writability/table checks | Expects `trades` plus `signals`, `orders`, `positions`, `deals`, `trades_normalized`; uses `sqlite_master`, `COUNT(*)`, and commit. |
| `packages/integrity/database/deep_health.py` | Schema, duplicate-ticket, timestamp, account, strategy, closure checks | `PRAGMA table_info(trades)`, `ticket`, `account`, `account_name`, `strategy_version`, `mt5_position_id`, `execution_contract_valid`, `entry_deviation_pips`, `timestamp`, `exit_time`, `mt5_closure_state`, and result values. |
| `packages/observability/reconciliation_daemon.py` | Reconciliation queries | Reads open/closed trade identity and closure fields; direct SQL and a production database path are embedded in the daemon. |
| `packages/execution/final_qualification_engine.py` | `print_final_qualification(trade_id)` | `SELECT * FROM trades WHERE id = ?`; maps the result using cursor description, then consumes evidence fields such as `signal_age_ms`, `actual_entry`, `actual_sl`, `actual_tp`, `risk_budget_usd`, `mt5_position_id`, and `execution_contract_valid`. |
| `packages/execution/orphan_detector.py` | Broker-position orphan check | Looks up `SELECT id FROM trades WHERE ticket = ?`; uses broker position ticket, not database id. It also initializes MT5 when run, so it is excluded from tests. |
| `packages/strategy/model_validation.py`, `ai-service/check_memory.py`, `ai-service/feature_analysis.py`, `ai-service/show_history.py`, `ai-service/sync_memory.py`, `ai-service/sync_positions.py` | Research/validation/memory/reporting reads and selected writes | Direct SQLite access to `trades` and/or related historical tables; these are not part of the eight-method logger surface. |

The complete historical/tooling inventory found by source search is grouped below. These files must be treated as direct-schema dependencies during migration, even where they are not production startup paths:

`tools/` — `add_account_filtering.py`, `add_execution_fields.py`, `add_planned_columns.py`, `add_version_column.py`, `analyze_id163_execution.py`, `audit_id164.py`, `audit_mt5_deals.py`, `audit_v3_sizing.py`, `blocked_vs_exception.py`, `bug_dashboard.py`, `check_id165.py`, `check_new_trades.py`, `check_recent_trades.py`, `cleanup_historical.py`, `complete_evidence_columns.py`, `control_plane.py`, `dashboard_data.py`, `detailed_qualification.py`, `diagnostics.py`, `evidence_based_audit.py`, `final_advisor_report.py`, `final_cleanup.py`, `final_verification.py`, `find_bad_ts.py`, `find_timestamp_issue.py`, `fix_closed_pnl.py`, `fix_closure_and_risk_evidence.py`, `fix_daily_report.py`, `fix_execution_capture.py`, `fix_execution_contract.py`, `fix_id146.py`, `fix_id163_entry.py`, `fix_id163_sync.py`, `fix_id163_ts.py`, `fix_id165.py`, `fix_id165_ts.py`, `fix_order_correct.py`, `fix_qualification_source.py`, `fix_remaining_closed.py`, `fix_schema_defaults.py`, `fix_stale_trades.py`, `fix_strategy_tagging.py`, `fix_trade_logger.py`, `fix_trade_states.py`, `fix_v3_metadata.py`, `fix_v3_trade.py`, `ground_truth.py`, `improve_round3.py`, `inspect_v3_raw.py`, `investigate_floating_loss.py`, `investigate_id163_bypass.py`, `investigate_id164.py`, `investigate_trades.py`, `live_monitor.py`, `multi_gate_tracker.py`, `p0_id164_reconciliation.py`, `qualified_trade_check.py`, `qualified_trade_tracker.py`, `reconcile.py`, `reconcile_v3_positions.py`, `sync_id164_closed.py`, `sync_id165.py`, `sync_mt5_reality.py`, `sync_orphan_position.py`, `today_stats.py`, `trade_qualification.py`, `trade_summary.py`, `v3_daily_report.py`, `v3_frontend_data.py`, `v3_strategy_review.py`, `validation_gates.py`, `validation_mode.py`, `verify_advisor_recommendations.py`, `verify_cleanup.py`, `verify_evidence_complete.py`, `verify_for_advisor.py`, `verify_live_micro.py`, `verify_next_trade.py`, `verify_stats.py`, `verify_trading_state.py`, `verify_v3_state.py`, `verify_v3_trades.py`, and `yesterday_stats.py`.

`archive/` — `account_trades.py`, `add_v3_api.py`, `add_v3_backend.py`, `advisor_verification.py`, `check_decisions.py`, `check_live.py`, `check_trades.py`, `dashboard_final.py`, `dashboard_inst.py`, `dashboard_institutional.py`, `dashboard_pro.py`, `dashboard_v3_final.py`, `expectancy.py`, `final_health_check.py`, `final_verify.py`, `forensic_audit.py`, `quick_perf.py`, `quick_verify.py`, `r_analysis.py`, `r_by_hour.py`, `r_by_pair.py`, `r_by_session.py`, `r_clean.py`, `replay_audit.py`, `signal_bias.py`, `tag_data.py`, `tag_v3.py`, `v3_dashboard.py`, `v3_full_dashboard.py`, `verify_30day_plan.py`, `verify_account_tag.py`, `verify_all.py`, and `verify_options.py`.

`tests/characterization/` directly inspects the legacy table in the Phase 2/5/6/7 tests. No production database is used by those tests.

## Schema inventory

### Legacy `trades` columns created/managed by `TradeLogger`

All columns except `id` are nullable in the legacy DDL. There are no explicit defaults in the `trades` DDL. The logger supplies application-level defaults for the five institutional fields on entry. The listed SQLite types are the exact declared affinities in `risk/trade_logger.py`.

| Column | SQLite type | Classification | Produced by | Consumed by | Required by current callers? |
|---|---|---|---|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | core trade identity | SQLite | Qualification/tooling `WHERE id`, `SELECT *`, returned entry id | Yes for direct evidence tooling; not a logger method argument. |
| `timestamp` | `TEXT` | timestamp | `TradeLogger` naive `datetime.now().isoformat()` | daily stats, reports, timestamp checks, direct SQL | Yes. |
| `pair` | `TEXT` | core trade identity | entry signal | logger pair queries, dashboards/tools | Yes. |
| `signal` | `TEXT` | signal/planned trade data | entry signal | qualification, reports, direct SQL | Yes. |
| `confidence` | `REAL` | signal/planned trade data | entry signal | dashboards, performance stats, calibration | Yes. |
| `entry` | `REAL` | signal/planned trade data in legacy logger | entry signal | exit `pnl_percent`, qualification fallback, reports | Yes. |
| `stop_loss` | `REAL` | signal/planned trade data | entry signal | qualification fallback and reports | Yes. |
| `take_profit` | `REAL` | signal/planned trade data | entry signal | qualification fallback and reports | Yes. |
| `exit_price` | `REAL` | execution/actual trade data | exit logger/direct repair tools | reports and reconciliation | Yes for closure. |
| `exit_time` | `TEXT` | timestamp/execution state | exit logger/direct tools | closed filters, ordering, daily/query logic | Yes. |
| `pnl` | `REAL` | derived performance field / broker result | exit logger/direct tools | all performance consumers | Yes. |
| `pnl_percent` | `REAL` | derived performance field | exit logger | legacy row inspection/tools | Legacy-compatible but not used by logger aggregate queries. |
| `result` | `TEXT` | derived performance/state | exit logger/direct tools | dashboards, open/closed filters, health | Yes. |
| `volume` | `REAL` | execution/risk data | entry logger/direct tools | risk/qualification/reports | Yes for risk consumers. |
| `ticket` | `INTEGER` | broker/MT5 identity | broker result passed to logger | exit, orphan detection, direct tools | Yes; not unique. |
| `regime` | `TEXT` | strategy/model metadata | entry argument | regime performance, health, dashboards | Yes for allocation/health. |
| `reason` | `TEXT` | execution/evidence metadata | exit argument/direct tools | reports and exception evidence | Used by direct consumers. |
| `account` | `TEXT` | account identity | optional entry argument | drift, dashboard, health, direct SQL | Yes, but not consistently supplied. |
| `institutional_bias` | `TEXT` | institutional/evidence metadata | signal key or `NEUTRAL` | dashboard/grouping | Yes for dashboard grouping. |
| `institutional_score` | `REAL` | institutional/evidence metadata | signal key or `0` | direct reports/tools | Consumer-dependent. |
| `dealer_pressure` | `TEXT` | institutional/evidence metadata | signal key or `NEUTRAL` | dashboard/cache-related views/tools | Consumer-dependent. |
| `liquidity_state` | `TEXT` | institutional/evidence metadata | signal key or `NO_EVENT` | direct reports/tools | Consumer-dependent. |
| `continuation_prob` | `REAL` | strategy/model metadata | signal key or `0.50` | direct reports/tools | Consumer-dependent. |

Indexes created by the legacy logger are `idx_ticket`, `idx_pair`, `idx_exit_time`, `idx_account`, and `idx_regime`. `idx_ticket` is not declared `UNIQUE`.

### Extended fields required by direct consumers or alternate schema proposals

These fields are referenced by current code but are not created or written by the legacy `TradeLogger` migration. Their SQLite type on the deployed legacy `trades` table cannot be established without opening that database, which is prohibited in this phase.

| Columns | Classification | Consumers/role | Type status |
|---|---|---|---|
| `strategy_version`, `trade_mode`, `environment`, `model_version` | strategy/model and account context | dashboards, filters, validation, direct reports | `strategy_version` is used as text; other types are not defined by legacy logger. |
| `account_name`, `account_id`, `broker_server` | account identity | integrity, domain models, V2/normalized schemas, tools | Not in legacy logger DDL; types only defined in alternate schemas (`account_id INTEGER`, names/server TEXT). |
| `mt5_order_ticket`, `mt5_position_id`, `mt5_position_ticket`, `mt5_entry_deal_ticket`, `mt5_exit_deal_ticket`, `mt5_deal_ticket` | broker/MT5 identity | reconciliation, qualification, metrics, normalized/V2 schemas | Integer in alternate schemas where declared; legacy `ticket` remains a separate INTEGER broker-facing field. |
| `planned_entry`, `planned_sl`, `planned_tp`, `signal_entry`, `signal_sl`, `signal_tp` | signal/planned trade data | freshness, metrics, evidence, V2/normalized schemas | REAL in alternate schemas where declared; absent from legacy logger DDL. |
| `actual_entry`, `actual_sl`, `actual_tp`, `actual_exit`, `entry_deviation_pips`, `slippage_pips`, `slippage_entry_pips` | execution/actual trade data and derived fields | qualification, metrics, reconciliation, alternate schemas | REAL in alternate schemas where declared; absent from legacy logger DDL. |
| `signal_age_ms`, `spread_at_execution`, `risk_budget_usd`, `actual_risk_usd`, `risk_amount`, `risk_pct_of_balance`, `r_multiple` | risk/evidence/derived performance | qualification, metrics, evidence tools, V2 schema | Numeric usage is visible; exact legacy SQLite affinity is not established. |
| `execution_contract_valid`, `mt5_closure_state`, `reconciliation_status`, `reconciliation_checked_utc`, `reconciliation_issues`, `validation_errors`, `is_validated`, `data_version` | validation/reconciliation/compatibility | dashboards, health, qualification, tools, V2 schema | Integer/text usage is visible or defined only in alternate schema; absent from legacy logger DDL. |

The alternate `trades_v2` schema also defines `trade_id`, `signal_id`, UTC lifecycle timestamps, MT5 financial fields, provenance fields, and `comment`. The normalized schema separates `signals`, `orders`, `positions`, `deals`, and `trades_normalized`. Neither schema is adopted here.

## Identity semantics and Phase 8 blockers

### Database record ID

`log_trade_entry` returns `cursor.lastrowid`, which is the SQLite `trades.id`. It is not the broker ticket. `final_qualification_engine.py` and several tools use it to retrieve a row with `WHERE id = ?`. The Phase 7 method annotation calls this a backend record identifier, but the production compatibility boundary must preserve the distinction.

### Broker ticket and duplicate behavior

`ticket` is an indexed nullable INTEGER, not a unique key. The isolated characterization test demonstrates that two entries can share a ticket. `log_trade_exit`:

1. selects one open row with `WHERE ticket=? AND exit_time IS NULL` and `fetchone()`;
2. computes `pnl_percent` from that one row's `entry`; and
3. updates every row matching `WHERE ticket=?`, without `exit_time IS NULL` and without account scope.

Consequently, duplicate tickets receive the same exit data and the same computed percentage, even if their entry prices or accounts differ. Missing tickets are silent no-ops. The legacy code does not expose a separate MT5 position or deal identity.

### Account identity

The legacy logger writes only `account`, from an optional argument. `auto_trader_exness.py` passes no account on its entry call but passes `acc.name` to the drift query and uses account context around exit processing. Other consumers require `account_name`, and newer domain/schema code distinguishes `account_id`, `account_name`, `environment`, and broker server. These are therefore distinct concepts in the repository, inconsistently populated in the legacy table. The exit update does not scope by any account field.

### MT5 position/deal identity

`ticket` is used by legacy entry/exit and orphan lookup, but newer execution code distinguishes order ticket, position ticket, and deal ticket. `mt5_position_id` is used as a reconciliation/qualification field and is absent from `TradeLogger`'s schema and write path. It must not be treated as an alias for `trades.id` or legacy `ticket` during migration.

### Strategy and execution-contract fields

`strategy_version` and `execution_contract_valid` are direct-consumer filters/evidence fields, but neither is part of the Phase 7 logger method arguments or legacy entry INSERT. A future adapter cannot satisfy all current direct consumers by implementing only the eight methods.

## Planned versus actual execution

The legacy logger records signal values as `entry`, `stop_loss`, and `take_profit`; it records only `exit_price` for actual closure. It does not record actual fill entry, actual protective levels, planned-vs-actual deviation, order/deal price, or separate planned columns. The execution package and alternate schemas use `signal_entry`/`planned_entry` and `actual_entry`, plus corresponding SL/TP fields, but those are a separate evidence model and must not be silently mapped into legacy fields.

Current consumers depend on both models:

- legacy reports and exit percentage use `entry`;
- qualification falls back from `actual_entry` to `entry`, and from actual SL/TP to legacy SL/TP;
- metrics compare `planned_entry` to `actual_entry`;
- V2/normalized schemas explicitly separate signal, order, position, and deal prices.

## Schema lifecycle, transactions, and SQLite coupling

- Startup calls `CREATE TABLE IF NOT EXISTS`, then attempts additive `ALTER TABLE` statements while swallowing all exceptions. A partial table gains only the listed optional columns; missing base columns are not reconstructed.
- Index creation and migration commit through the shared connection.
- Entry commits its INSERT. A successful exit commits its UPDATE. A missing-ticket exit performs no write/commit. Query errors propagate. Exit database errors are caught and reported with the legacy warning print path.
- The connection is created with `check_same_thread=False`; `conn` and `cursor` remain public attributes and are directly inspected by characterization/tests/tooling. The logger shares one cursor and does not define an explicit concurrency/locking protocol.
- Direct consumers rely on SQLite syntax and behavior: `date(timestamp)`, `datetime('now')`, `sqlite_master`, `PRAGMA table_info`, `SELECT *` plus cursor description, SQLite `LIMIT` parameters, `LIKE`, and lexical TEXT timestamp comparisons.
- No file-backed DB was opened by Phase 8A. Concurrency and production lock behavior remain code-level risks, not runtime-characterized facts.

## Contract gap

The Phase 7 contract is sufficient for a compatibility façade around current `TradeLogger` callers. It is not sufficient as the complete production persistence boundary because it omits:

1. direct row access by database record id;
2. broker order/position/deal identity separate from `ticket`;
3. account id/name/environment scoping;
4. strategy/version and execution-contract evidence fields;
5. planned-vs-actual execution projections;
6. direct SQL/query projection compatibility;
7. schema initialization, migration reporting, connection lifecycle, and concurrency policy.

No contract correction is implemented in Phase 8A.

## Architecture options

### Option A — One expanded `CanonicalTradePersistenceContract`

Expand the existing eight methods with every identity, evidence, schema, and analytics concern. This minimizes the number of names during migration, but creates a large interface, couples writes to dashboard queries, and makes SQLite-era `SELECT *`/migration behavior part of the canonical API.

### Option B — Small logger plus separate boundaries

Keep the Phase 7 eight-method compatibility façade for current logger callers. Add, in a later approved phase, separate contracts for:

- trade persistence commands and legacy projections;
- execution identity and reconciliation;
- analytics/query/read models;
- schema/migration and connection lifecycle.

Direct SQL consumers migrate to read projections or query services without forcing their fields into the trade-write interface. This requires an explicit compatibility projection for legacy `trades` rows.

### Option C — Generic repository/query service

Expose a generic record repository and query API covering all current SQL consumers. This can absorb the current surface quickly, but it preserves raw schema coupling, hides identity semantics behind untyped records, and risks recreating SQLite as the de facto contract.

## Recommended architecture

Option B is the smallest safe architecture:

1. retain the Phase 7 logger contract unchanged for the existing `TradeLogger` callers;
2. later add a narrow legacy-trade projection/read boundary for direct SQL consumers;
3. keep database record id, broker order ticket, position ticket, and deal ticket as distinct values;
4. introduce account-scoped identity explicitly at the execution/persistence boundary without changing legacy rows;
5. add planned-vs-actual execution and evidence contracts separately when their producers and consumers are characterized.

This preserves current callers, avoids exposing SQLite internals to new code, and permits a backend adapter later without forcing dashboard, analytics, reconciliation, and schema migration into the logger write interface.

## Remaining risks

- The deployed `trades` database schema was intentionally not inspected; extended-column presence and affinities remain unverified.
- Direct SQL consumers remain coupled to the legacy table and may fail against a minimal legacy schema.
- Duplicate-ticket updates are broad and unscoped by account or row id.
- `account`/`account_name` and planned/actual fields are inconsistently populated.
- Shared SQLite connection/cursor behavior under concurrent access is not characterized.
- Some service/dashboard code combines database reads with MT5 or cache access; those side effects require separate boundaries.

