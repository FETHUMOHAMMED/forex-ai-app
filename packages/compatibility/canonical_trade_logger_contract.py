"""Canonical, backend-neutral persistence contract for trade records.

This module defines the interface and compatibility clauses only.  It does
not open databases, perform migrations, normalize legacy data, or provide a
production implementation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional, Protocol, TypedDict, runtime_checkable


class DailyStats(TypedDict):
    date: str
    total_trades: int
    winning_trades: int
    total_pnl: float
    win_rate: float


EntrySignal = Mapping[str, Any]
PerformanceStats = Mapping[str, Any]
RegimePerformance = Mapping[str, Mapping[str, Any]]
PairPerformance = Mapping[str, Mapping[str, Any]]


REQUIRED_COMPATIBILITY_BEHAVIORS: tuple[str, ...] = (
    "entry accepts the legacy signal and optional volume/ticket/regime/account arguments",
    "exit accepts ticket, exit_price, exit_time, pnl, and optional reason",
    "query method names, arguments, return shapes, and value semantics remain compatible",
    "successful entry and exit operations commit their own persistence changes",
    "missing exit tickets do not create a new trade record",
)


LEGACY_QUIRKS: tuple[str, ...] = (
    "partial-schema migration adds optional columns but does not reconstruct missing base columns",
    "entry timestamps are naive datetime.now().isoformat() values",
    "pnl_percent is calculated as pnl divided by entry multiplied by 100",
    "zero PnL receives an empty result string",
    "missing-ticket exits are silent no-ops",
    "profit_factor is capped at 5.0 in regime and pair performance queries",
    "query failures propagate from the underlying database connection",
    "exit database errors are caught and reported through the legacy warning print path",
)


FUTURE_IMPROVEMENTS: tuple[str, ...] = (
    "timezone-aware UTC timestamps",
    "explicit schema/version migration reporting",
    "validated typed entry and exit records",
    "structured persistence error results instead of print-based reporting",
    "idempotency and event identity guarantees",
    "separate planned, actual, broker, and deal values where approved",
)


@runtime_checkable
class CanonicalTradeLoggerContract(Protocol):
    """Interface required by future persistence implementations.

    Implementations must preserve the compatibility clauses above until a
    separately approved migration changes them.  The protocol intentionally
    does not specify a database, schema, connection lifecycle, or backend.
    """

    def log_trade_entry(
        self,
        signal: EntrySignal,
        volume: Optional[float] = None,
        ticket: Optional[int] = None,
        regime: Optional[str] = None,
        account: Optional[str] = None,
    ) -> int:
        """Persist an entry and return its backend record identifier."""

    def log_trade_exit(
        self,
        ticket: int,
        exit_price: float,
        exit_time: datetime,
        pnl: float,
        reason: str = "",
    ) -> None:
        """Apply exit data to the matching persisted trade, if present."""

    def get_recent_pnls(self, limit: int = 100) -> list[float]:
        """Return recent closed-trade PnL values in legacy ordering."""

    def get_recent_trade_stats(
        self, days: int = 30, account: Optional[str] = None
    ) -> tuple[int, int, float]:
        """Return total closed trades, wins, and percentage win rate."""

    def get_regime_performance(self, days: int = 30) -> RegimePerformance:
        """Return the legacy per-regime aggregate mapping."""

    def get_pair_performance(self, days: int = 30) -> PairPerformance:
        """Return the legacy per-pair aggregate mapping."""

    def get_daily_stats(self, date: Optional[str] = None) -> Optional[DailyStats]:
        """Return legacy daily statistics or None when no trades qualify."""

    def get_performance_stats(self) -> PerformanceStats:
        """Return the legacy formatted aggregate performance mapping."""
