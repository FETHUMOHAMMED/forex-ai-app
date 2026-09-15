# Phase 7 canonical persistence contract

Phase 7 defines a backend-neutral contract for the legacy trade-persistence
boundary. It does not create a database backend, change callers, migrate
production data, or alter the Phase 3–6 adapters.

## Canonical interface

`CanonicalTradeLoggerContract` defines these methods:

- `log_trade_entry(signal, volume=None, ticket=None, regime=None, account=None) -> int`
- `log_trade_exit(ticket, exit_price, exit_time, pnl, reason="") -> None`
- `get_recent_pnls(limit=100) -> list[float]`
- `get_recent_trade_stats(days=30, account=None) -> (total, wins, win_rate_percent)`
- `get_regime_performance(days=30) -> mapping`
- `get_pair_performance(days=30) -> mapping`
- `get_daily_stats(date=None) -> mapping | None`
- `get_performance_stats() -> mapping`

The contract accepts a mapping for `signal` and requires the six currently
consumed fields: `pair`, `signal`, `confidence`, `entry`, `stop_loss`, and
`take_profit`. Existing institutional metadata remains optional and is not
made a new canonical requirement.

## Required compatibility behavior

Until a separately approved breaking migration, implementations must preserve
the method names, arguments, return shapes, per-operation commit expectation,
and missing-ticket no-op behavior used by the legacy callers.

## Legacy quirks preserved for parity

- Partial-schema migration adds optional columns but does not reconstruct
  missing base columns.
- Entry timestamps are naive `datetime.now().isoformat()` values.
- `pnl_percent` is `pnl / entry * 100`.
- Zero PnL produces an empty result string.
- Missing-ticket exits are silent no-ops.
- Regime and pair profit factors are capped at `5.0`.
- Query failures propagate from the backend.
- Exit database failures follow the legacy caught-error and warning-print
  behavior.

These are compatibility requirements for the current migration, not design
recommendations.

## Future improvements, not implemented

Potential future work includes UTC-aware timestamps, explicit migration
reporting, typed validation, structured error results, idempotency/event
identity, and clearer planned-versus-actual trade fields. None is implemented
or implied by this contract.

## Transaction and timestamp semantics

The contract requires successful entry and exit operations to persist their
own changes, matching the legacy per-operation commit behavior. It does not
require a shared transaction across multiple calls or define a new connection
lifecycle. Entry timestamp generation remains implementation-defined but must
remain legacy-compatible during parity work; the current legacy value is a
naive ISO timestamp.

## Verification boundary

Tests bind the contract to the existing legacy logger through the Phase 6
shadow adapter using only SQLite `:memory:` databases. No production database,
MT5, broker, network, cache, or launcher is used.
