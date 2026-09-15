# Phase 5 legacy TradeLogger characterization

Phase 5 characterizes the legacy `risk.trade_logger.TradeLogger` boundary
without touching the production `trades.db`.

## Boundary and safety

Each test creates an isolated SQLite `:memory:` database and closes it during
cleanup. The partial-schema case uses an already-created in-memory connection
to exercise the legacy migration code without creating a file. The production
logger, auto-trader, broker, signal service, cache, launcher, and runtime
configuration are not modified or started.

No compatibility adapter was added in this phase. The existing Phase 3
persistence adapter remains unchanged; this phase records the legacy behavior
before any persistence replacement is considered.

## Characterized behavior

- Startup creates the legacy `trades` schema and five indexes.
- Startup attempts additive column migration and is idempotent on a second
  initialization.
- Entry writes exact signal, risk-plan, account, regime, ticket, and
  institutional fields.
- Entry timestamps are generated dynamically with naive ISO formatting; tests
  compare them only to the invocation interval.
- Missing institutional signal fields use the legacy defaults.
- Exit updates calculate `pnl_percent` as `pnl / entry * 100`, classify positive
  PnL as `WIN`, negative PnL as `LOSS`, and zero PnL as an empty result.
- Missing exit tickets are a no-op.
- Query return shapes, date filters, regime/pair aggregation, daily stats, and
  formatted aggregate statistics are preserved.
- Query failures propagate from a closed connection, while exit-update
  failures are caught and return `None` after printing the legacy warning.

No timestamp is broadly normalized, and no persistence behavior is corrected.
