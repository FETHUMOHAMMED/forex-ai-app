"""Shadow-only Phase 8C persistence boundary.

This adapter delegates the characterized legacy entry/exit operations without
adding persistence, identity, schema, account, or execution semantics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional

from .legacy_trade_logger_shadow import (
    ShadowModeViolation,
    ShadowTradeLoggerAdapter,
)


class ShadowCanonicalTradePersistenceAdapter:
    """Delegate legacy entry/exit persistence in an isolated shadow mode.

    The wrapped logger must be explicitly marked ``shadow_only`` and must use
    an in-memory SQLite connection.  The legacy ``ticket`` value is forwarded
    unchanged; this class does not interpret it as an order, position, or deal
    ticket.
    """

    shadow_only = True

    def __init__(self, legacy_logger: Any, *, shadow_only: bool = False):
        if shadow_only is not True:
            raise ShadowModeViolation(
                "ShadowCanonicalTradePersistenceAdapter requires shadow_only=True"
            )
        self._legacy = ShadowTradeLoggerAdapter(legacy_logger)

    def log_trade_entry(
        self,
        signal: Mapping[str, Any],
        volume: Optional[float] = None,
        ticket: Optional[int] = None,
        regime: Optional[str] = None,
        account: Optional[str] = None,
    ) -> int:
        """Delegate legacy entry persistence and return the legacy row id."""

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
        """Delegate legacy ticket-based exit behavior unchanged."""

        return self._legacy.log_trade_exit(
            ticket=ticket,
            exit_price=exit_price,
            exit_time=exit_time,
            pnl=pnl,
            reason=reason,
        )

