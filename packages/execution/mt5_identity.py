"""MT5 Ticket Identity Model - Distinguishes ALL ticket types.
The critical insight: order_ticket != position_ticket != deal_ticket.
Each must be stored separately for accurate reconciliation.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TicketType(str, Enum):
    ORDER = "ORDER"          # mt5.order_send().order
    POSITION = "POSITION"    # mt5.positions_get()[].ticket  
    DEAL_ENTRY = "DEAL_ENTRY"  # mt5.history_deals_get(entry=0)
    DEAL_EXIT = "DEAL_EXIT"    # mt5.history_deals_get(entry=1)

@dataclass(frozen=True)
class MT5Ticket:
    """Immutable MT5 ticket - prevents type confusion"""
    ticket_id: int
    ticket_type: TicketType
    symbol: str
    timestamp_utc: datetime
    
    def __repr__(self):
        return f"{self.ticket_type.value}#{self.ticket_id}"

@dataclass
class TradeIdentity:
    """Complete trade identity chain - links ALL ticket types.
    
    This replaces the old single 'ticket' column that conflated
    orders, positions, and deals into one ambiguous number.
    """
    # Strategy-level identity
    strategy_trade_id: str              # e.g., "V3_LiveMicro_20260811_001"
    signal_id: str                      # AI signal that triggered this trade
    
    # Account identity (immutable for this trade)
    account_id: int                     # e.g., REDACTED_LIVE_ACCOUNT
    account_name: str                   # e.g., "Live_Micro"
    
    # MT5 Order identity
    order_request_id: Optional[str] = None    # Internal request ID
    mt5_order_ticket: Optional[int] = None    # mt5.order_send().order
    mt5_order_retcode: Optional[int] = None   # Result of order_send
    
    # MT5 Position identity
    mt5_position_ticket: Optional[int] = None  # mt5.positions_get()[].ticket
    
    # MT5 Deal identity  
    mt5_entry_deal_ticket: Optional[int] = None  # Deal that opened position
    mt5_exit_deal_ticket: Optional[int] = None   # Deal that closed position
    
    # Actual execution prices (from MT5 deals, NOT signal)
    actual_entry_price: Optional[float] = None
    actual_exit_price: Optional[float] = None
    actual_volume: Optional[float] = None
    
    # Financial result (from MT5 deals)
    mt5_profit: Optional[float] = None
    mt5_commission: Optional[float] = None
    mt5_swap: Optional[float] = None
    
    @property
    def mt5_net_pnl(self) -> Optional[float]:
        """Net P&L from MT5 (profit + commission + swap)"""
        if self.mt5_profit is None:
            return None
        return (self.mt5_profit or 0) + (self.mt5_commission or 0) + (self.mt5_swap or 0)
    
    @property
    def has_order(self) -> bool:
        return self.mt5_order_ticket is not None
    
    @property
    def has_position(self) -> bool:
        return self.mt5_position_ticket is not None
    
    @property
    def has_entry_deal(self) -> bool:
        return self.mt5_entry_deal_ticket is not None
    
    @property
    def has_exit_deal(self) -> bool:
        return self.mt5_exit_deal_ticket is not None
    
    @property
    def is_complete(self) -> bool:
        """Trade has gone through full MT5 lifecycle"""
        return all([
            self.has_order,
            self.has_position,
            self.has_entry_deal,
            self.has_exit_deal,
        ])
    
    @property
    def is_phantom(self) -> bool:
        """Trade exists in DB but not in MT5"""
        return not self.has_position and not self.has_order
    
    def identity_summary(self) -> str:
        """Human-readable identity chain"""
        lines = [
            f"Trade: {self.strategy_trade_id}",
            f"  Signal: {self.signal_id}",
            f"  Account: {self.account_name} ({self.account_id})",
            f"  Order: {MT5Ticket(self.mt5_order_ticket, TicketType.ORDER, '', None) if self.mt5_order_ticket else 'N/A'}",
            f"  Position: {MT5Ticket(self.mt5_position_ticket, TicketType.POSITION, '', None) if self.mt5_position_ticket else 'N/A'}",
            f"  Entry Deal: {MT5Ticket(self.mt5_entry_deal_ticket, TicketType.DEAL_ENTRY, '', None) if self.mt5_entry_deal_ticket else 'N/A'}",
            f"  Exit Deal: {MT5Ticket(self.mt5_exit_deal_ticket, TicketType.DEAL_EXIT, '', None) if self.mt5_exit_deal_ticket else 'N/A'}",
        ]
        if self.is_complete:
            lines.append(f"  Status: COMPLETE - Net PnL: ${self.mt5_net_pnl:.2f}")
        elif self.is_phantom:
            lines.append(f"  Status: PHANTOM - No MT5 records found")
        else:
            lines.append(f"  Status: INCOMPLETE")
        return "\n".join(lines)


def create_trade_identity(
    strategy_trade_id: str,
    signal_id: str,
    account_id: int,
    account_name: str,
    mt5_position_ticket: Optional[int] = None,
    mt5_order_ticket: Optional[int] = None,
    order_retcode: Optional[int] = None,
) -> TradeIdentity:
    """Factory function - creates identity at order time"""
    return TradeIdentity(
        strategy_trade_id=strategy_trade_id,
        signal_id=signal_id,
        account_id=account_id,
        account_name=account_name,
        mt5_order_ticket=mt5_order_ticket,
        mt5_order_retcode=order_retcode,
        mt5_position_ticket=mt5_position_ticket,
    )


def reconcile_with_mt5(
    identity: TradeIdentity,
    mt5_deals: List[dict],
) -> TradeIdentity:
    """Reconcile a trade identity with actual MT5 deals.
    
    Args:
        identity: The trade identity to reconcile
        mt5_deals: List of deals from mt5.history_deals_get(position=identity.mt5_position_ticket)
    
    Returns:
        Updated TradeIdentity with deal and financial data
    """
    for deal in mt5_deals:
        # entry=0 means position OPEN, entry=1 means position CLOSE
        if deal.get('entry') == 0:  # IN
            identity.mt5_entry_deal_ticket = deal.get('ticket')
            identity.actual_entry_price = deal.get('price')
            identity.actual_volume = deal.get('volume')
        elif deal.get('entry') == 1:  # OUT
            identity.mt5_exit_deal_ticket = deal.get('ticket')
            identity.actual_exit_price = deal.get('price')
            identity.mt5_profit = deal.get('profit')
            identity.mt5_commission = deal.get('commission')
            identity.mt5_swap = deal.get('swap')
    
    return identity
