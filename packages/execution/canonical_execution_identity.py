"""Pure Phase 12 execution-identity and account-scope value types.

This module has no database, MT5, broker, network, configuration, or
reconciliation dependencies.  It intentionally does not convert the legacy
``trades.ticket`` value into any typed execution identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


def _require_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def _require_positive_int(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")


@dataclass(frozen=True)
class AccountScope:
    """Explicit broker/account namespace for all typed execution identities."""

    broker: str
    login: int
    server: str
    environment: str
    local_account_id: Optional[str] = None

    def __post_init__(self) -> None:
        _require_text(self.broker, "broker")
        _require_positive_int(self.login, "login")
        _require_text(self.server, "server")
        _require_text(self.environment, "environment")
        if self.local_account_id is not None:
            _require_text(self.local_account_id, "local_account_id")


@dataclass(frozen=True)
class TradeRecordId:
    """Local SQLite/application record identity, not a broker identity."""

    value: int

    def __post_init__(self) -> None:
        _require_positive_int(self.value, "trade_record_id")


@dataclass(frozen=True)
class LegacyTicketValue:
    """Opaque legacy ``trades.ticket`` value with no execution type."""

    value: int

    def __post_init__(self) -> None:
        _require_positive_int(self.value, "legacy_ticket")


@dataclass(frozen=True)
class OrderIdentity:
    """Typed MT5 order identity scoped to one broker account namespace."""

    account: AccountScope
    ticket_id: int

    def __post_init__(self) -> None:
        _require_positive_int(self.ticket_id, "order_ticket")


@dataclass(frozen=True)
class PositionIdentity:
    """Typed MT5 position identity scoped to one broker account namespace."""

    account: AccountScope
    ticket_id: int

    def __post_init__(self) -> None:
        _require_positive_int(self.ticket_id, "position_ticket")


class DealRole(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


@dataclass(frozen=True)
class DealIdentity:
    """Typed MT5 deal identity, optionally linked to a position."""

    account: AccountScope
    ticket_id: int
    role: DealRole
    position: Optional[PositionIdentity] = None

    def __post_init__(self) -> None:
        _require_positive_int(self.ticket_id, "deal_ticket")
        if self.position is not None and self.position.account != self.account:
            raise ValueError("deal and position must share the same account scope")


@dataclass(frozen=True)
class DealExecution:
    """Observed execution facts attached to a typed deal identity.

    These facts are observations, not reconciliation decisions.  Optional
    fields allow incomplete or out-of-order broker events to be represented.
    """

    identity: DealIdentity
    quantity: Optional[float] = None
    price: Optional[float] = None
    execution_time: Optional[datetime] = None
    source_event_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("quantity must be positive when present")
        if self.price is not None and self.price <= 0:
            raise ValueError("price must be positive when present")
        if self.source_event_id is not None:
            _require_text(self.source_event_id, "source_event_id")


@dataclass(frozen=True)
class ExecutionLineage:
    """Immutable identity references for one local trade lineage.

    Multiple entry and exit deal observations are intentionally allowed.  This
    represents partial fills, partial closes, duplicate observations, and
    out-of-order arrival without deduplicating or reconciling them.  Those
    decisions belong to a separate reconciliation boundary.
    """

    account: AccountScope
    local_trade_record_id: Optional[TradeRecordId] = None
    order: Optional[OrderIdentity] = None
    position: Optional[PositionIdentity] = None
    entry_deals: tuple[DealExecution, ...] = ()
    exit_deals: tuple[DealExecution, ...] = ()

    def __post_init__(self) -> None:
        identities = []
        if self.order is not None:
            identities.append(self.order.account)
        if self.position is not None:
            identities.append(self.position.account)
        identities.extend(deal.identity.account for deal in self.entry_deals)
        identities.extend(deal.identity.account for deal in self.exit_deals)
        if any(identity != self.account for identity in identities):
            raise ValueError("all lineage identities must share the account scope")

        for deal in self.entry_deals:
            if deal.identity.role is not DealRole.ENTRY:
                raise ValueError("entry_deals must contain ENTRY deal identities")
            if (
                self.position is not None
                and deal.identity.position is not None
                and deal.identity.position != self.position
            ):
                raise ValueError("entry deal references a different position")
        for deal in self.exit_deals:
            if deal.identity.role is not DealRole.EXIT:
                raise ValueError("exit_deals must contain EXIT deal identities")
            if (
                self.position is not None
                and deal.identity.position is not None
                and deal.identity.position != self.position
            ):
                raise ValueError("exit deal references a different position")


__all__ = [
    "AccountScope",
    "TradeRecordId",
    "LegacyTicketValue",
    "OrderIdentity",
    "PositionIdentity",
    "DealRole",
    "DealIdentity",
    "DealExecution",
    "ExecutionLineage",
]
