"""Isolated Phase 10 eight-method logger façade characterization.

This module is intentionally a thin delegator.  It is not imported by a
production launcher and does not create a database connection.  The injected
legacy logger remains responsible for all persistence, SQL, schema, lifecycle,
transaction, timestamp, error, account, and ticket behavior.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from .canonical_trade_logger_contract import (
    CanonicalTradeLoggerContract,
    DailyStats,
    EntrySignal,
    PairPerformance,
    PerformanceStats,
    RegimePerformance,
)


class CanonicalTradeLoggerFacade:
    """Delegate the complete Phase 7 contract to an unchanged logger.

    This is a composition-boundary characterization artifact.  It deliberately
    does not expose the wrapped logger's connection or cursor and does not add
    any behavior around delegated calls.
    """

    def __init__(self, legacy_logger: CanonicalTradeLoggerContract):
        self._legacy = legacy_logger

    def log_trade_entry(
        self,
        signal: EntrySignal,
        volume: Optional[float] = None,
        ticket: Optional[int] = None,
        regime: Optional[str] = None,
        account: Optional[str] = None,
    ) -> int:
        return self._legacy.log_trade_entry(
            signal,
            volume=volume,
            ticket=ticket,
            regime=regime,
            account=account,
        )

    def log_trade_exit(
        self,
        ticket: int,
        exit_price: float,
        exit_time: datetime,
        pnl: float,
        reason: str = "",
    ) -> None:
        return self._legacy.log_trade_exit(
            ticket=ticket,
            exit_price=exit_price,
            exit_time=exit_time,
            pnl=pnl,
            reason=reason,
        )

    def get_recent_pnls(self, limit: int = 100) -> list[float]:
        return self._legacy.get_recent_pnls(limit=limit)

    def get_recent_trade_stats(
        self, days: int = 30, account: Optional[str] = None
    ) -> tuple[int, int, float]:
        return self._legacy.get_recent_trade_stats(days=days, account=account)

    def get_regime_performance(self, days: int = 30) -> RegimePerformance:
        return self._legacy.get_regime_performance(days=days)

    def get_pair_performance(self, days: int = 30) -> PairPerformance:
        return self._legacy.get_pair_performance(days=days)

    def get_daily_stats(self, date: Optional[str] = None) -> Optional[DailyStats]:
        return self._legacy.get_daily_stats(date=date)

    def get_performance_stats(self) -> PerformanceStats:
        return self._legacy.get_performance_stats()


__all__ = ["CanonicalTradeLoggerFacade"]
