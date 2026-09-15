# Phase 10 Eight-Method Production Persistence Façade Characterization

## Status and boundary

Phase 10 characterizes a possible composition boundary only. The façade in
`packages/compatibility/canonical_trade_logger_facade.py` is an isolated
delegator and is not production wiring.

No production caller imports it. `AccountState.logger` remains unchanged and
continues to use the current production `TradeLogger`.

The façade creates no database connection and contains no SQL, schema logic,
MT5 logic, broker logic, identity mapping, account normalization, retry logic,
transaction logic, analytics transformation, or lifecycle policy.

## Evidence-supported contract

The Phase 7 `CanonicalTradeLoggerContract` remains exactly eight methods:

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

The façade preserves these signatures and forwards arguments without changing
their meaning.

## Delegation fidelity

Each façade method delegates directly to the corresponding method on the
injected legacy logger. The legacy logger remains the actual backend.

### Entry

Characterized behavior preserved by delegation:

- normal and omitted tickets;
- nullable ticket and account values;
- duplicate tickets;
- supplied and omitted accounts;
- SQLite `lastrowid` return value;
- planned `entry`, `stop_loss`, and `take_profit` values;
- requested `volume`;
- per-entry commit behavior;
- entry exception propagation.

### Exit

Characterized behavior preserved by delegation:

- ticket-only matching;
- missing-ticket silent no-op;
- duplicate-ticket broad update behavior;
- no account-scoped exit matching;
- supplied exit price, time, PnL, and reason;
- per-exit commit behavior when a row is updated;
- legacy caught database errors and warning-print behavior.

### Queries

The six query methods are delegated without filtering, sorting, date,
aggregation, NULL, account, formatting, or exception changes. Their observed
legacy return shapes remain authoritative:

- recent PnLs: list ordered by legacy `exit_time DESC`;
- recent trade statistics: `(total, wins, win_rate_percent)`;
- regime performance: nested aggregate mapping with legacy profit-factor cap;
- pair performance: nested aggregate mapping with legacy profit-factor cap;
- daily statistics: mapping or `None`;
- aggregate performance: legacy formatted mapping, including empty-result
  behavior.

Dynamic timestamps are not compared byte-for-byte between separate logger
calls. They are required to remain parseable ISO timestamps; deterministic
fields and all returned query values are compared exactly.

## Identity and account semantics

The façade treats `ticket` as opaque. It does not introduce `TicketType`,
`order_ticket`, `position_ticket`, or `deal_ticket` aliases and does not import
`packages/execution/mt5_identity.py`.

SQLite record IDs remain backend record IDs returned by legacy `lastrowid`.
They are not broker or MT5 identities.

The optional legacy `account` argument is forwarded exactly. No mapping to
`account_name`, `account_id`, login, environment, or server is introduced.
Exit remains ticket-only and unscoped by account.

## Planned versus actual fields

The façade does not transform fields. Legacy planned values remain legacy
`entry`, `stop_loss`, and `take_profit` values. It does not create or infer
actual entry, actual SL/TP, actual volume, MT5 profit, commission, swap, risk,
deviation, or reconciliation fields.

## Lifecycle and concurrency

The wrapped logger retains its observed legacy behavior:

- it owns the SQLite connection and cursor it creates;
- `conn` and `cursor` are public on the legacy object;
- the connection uses `check_same_thread=False`;
- construction performs legacy schema initialization/migration attempts;
- successful writes commit independently;
- query errors propagate;
- exit database errors are caught and printed;
- no explicit legacy close protocol is defined.

The façade does not expose a new close method, transaction scope, connection
ownership rule, or concurrency protocol. Concurrency remains unresolved and is
not redesigned by this phase.

## Direct SQL status

Dashboard, health, observability, reconciliation, qualification, research,
validation, synchronization, and schema-experiment SQL consumers remain out of
scope. The façade is not a generic repository and does not replace `SELECT *`,
`PRAGMA`, cursor shapes, SQLite date functions, direct updates, or schema
inspection.

## Production status

The façade is not imported by `auto_trader_exness.py`, `broker_exness.py`, any
launcher, dashboard, or production composition root. No production database,
MT5 terminal, broker API, network service, cache, configuration, or runtime
state is accessed by the characterization.

## Phase 10 conclusion

The repository evidence supports a behavior-preserving eight-method
composition boundary when it delegates directly to the unchanged legacy
`TradeLogger`. This does not authorize production wiring. A future production
integration would still require separate approval, complete dependency-backed
parity, and resolution of direct SQL, identity, account, lifecycle, and
concurrency risks.
