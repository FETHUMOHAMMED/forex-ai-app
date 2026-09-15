# Phase 6 shadow TradeLogger compatibility wrapper

Phase 6 adds a persistence-specific shadow adapter around the characterized
legacy `risk.trade_logger.TradeLogger`.

## Safety boundary

`ShadowTradeLoggerAdapter` delegates to the legacy logger only when:

- the logger is explicitly marked `shadow_only = True`; and
- its SQLite connection reports an in-memory database through
  `PRAGMA database_list`.

Unmarked loggers and file-backed connections are rejected. The adapter never
opens a database, creates a schema, writes a cache, or participates in a
production launcher.

## Parity scope

The tests compare legacy and shadow behavior for:

- entry and exit rows;
- recent PnL and trade statistics;
- regime and pair performance;
- daily and formatted aggregate statistics;
- missing-ticket no-op behavior; and
- closed-connection error propagation.

Dynamic entry timestamps are excluded only from row comparison because the two
calls occur at different instants. All persisted deterministic fields and
query results are compared exactly.

Existing Phase 3 persistence delegation remains unchanged. This wrapper is
offline-only and is not wired into the auto-trader or any production startup
path.
