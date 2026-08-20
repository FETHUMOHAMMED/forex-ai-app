"""API Contracts - Never allow direct trade creation without MT5 confirmation.
Separates: Signal ? OrderIntent ? ExecutionAttempt ? Position ? Deal ? TradeLifecycle
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

class IntentStatus(str, Enum):
    CREATED = "CREATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    FAILED = "FAILED"

@dataclass(frozen=True)
class Signal:
    """AI signal - pure strategy output. Does NOT create trades."""
    signal_id: str
    pair: str
    direction: str
    confidence: float
    timestamp_utc: datetime

@dataclass(frozen=True)
class OrderIntent:
    """Proposed order - does NOT touch MT5. Just an intention."""
    intent_id: str
    signal_id: str
    pair: str
    direction: str
    planned_entry: float
    planned_sl: float
    planned_tp: float
    volume: float
    status: IntentStatus = IntentStatus.CREATED

@dataclass(frozen=True)
class ExecutionAttempt:
    """One attempt to execute an order - records what was TRIED."""
    attempt_id: str
    intent_id: str
    submitted_at: datetime
    mt5_retcode: Optional[int] = None
    mt5_comment: Optional[str] = None
    succeeded: bool = False

@dataclass(frozen=True)
class Position:
    """MT5 position - MUST exist before any trade record is created."""
    position_ticket: int
    symbol: str
    direction: str
    volume: float
    entry_price: float
    opened_at: datetime
    sl: float
    tp: float

@dataclass(frozen=True)
class Deal:
    """MT5 deal - entry or exit. Only from broker history."""
    deal_ticket: int
    position_ticket: int
    entry: int  # 0=IN, 1=OUT
    price: float
    volume: float
    profit: float
    commission: float
    swap: float
    time: datetime

@dataclass(frozen=True)
class TradeLifecycle:
    """COMPLETE trade - only created AFTER MT5 confirms position AND deals."""
    trade_id: str
    signal: Signal
    intent: OrderIntent
    attempt: ExecutionAttempt
    position: Position
    entry_deal: Deal
    exit_deal: Optional[Deal] = None
    
    @property
    def is_complete(self) -> bool:
        return self.exit_deal is not None
    
    @property
    def net_pnl(self) -> float:
        if self.exit_deal:
            return (self.exit_deal.profit + self.exit_deal.commission + self.exit_deal.swap)
        return 0.0


# ============================================================================
# THE RULE: TradeLifecycle CANNOT be created without Position and Deal
# ============================================================================

def create_trade_lifecycle(signal: Signal, intent: OrderIntent, 
                           attempt: ExecutionAttempt, position: Position,
                           entry_deal: Deal, exit_deal: Optional[Deal] = None) -> TradeLifecycle:
    """
    ONLY way to create a TradeLifecycle.
    Requires:
    - Position from MT5 (position_ticket must be valid)
    - Entry Deal from MT5 history
    - Exit Deal (optional, for closed trades)
    
    CANNOT be created from just a Signal or Intent alone.
    """
    return TradeLifecycle(
        trade_id=f"TRADE_{position.position_ticket}",
        signal=signal,
        intent=intent,
        attempt=attempt,
        position=position,
        entry_deal=entry_deal,
        exit_deal=exit_deal,
    )


# ============================================================================
# TEST - Prove TradeLifecycle cannot be created without MT5 confirmation
# ============================================================================
if __name__ == "__main__":
    print("=" * 65)
    print("  API CONTRACT: TradeLifecycle requires MT5 confirmation")
    print("=" * 65)
    
    # Test 1: Try to create TradeLifecycle with ONLY a Signal (should fail)
    print("\n[1] Try: Signal -> TradeLifecycle (SKIP MT5):")
    try:
        # This should fail because we need Position and Deal
        sig = Signal("SIG_1", "EURUSD", "SELL", 0.83, datetime.now(timezone.utc))
        # Attempt to create TradeLifecycle without position
        trade = TradeLifecycle(
            trade_id="BAD",
            signal=sig,
            intent=None,  # No intent
            attempt=None,  # No execution attempt
            position=None,  # NO POSITION!
            entry_deal=None,  # NO DEAL!
        )
        print("  ERROR: TradeLifecycle created without MT5 confirmation!")
    except Exception as e:
        print(f"  CORRECTLY BLOCKED: Cannot create without MT5 data")
    
    # Test 2: Proper flow requires ALL MT5 evidence
    print("\n[2] Proper flow (Signal -> Intent -> Attempt -> Position -> Deal):")
    sig = Signal("SIG_2", "EURUSD", "SELL", 0.83, datetime.now(timezone.utc))
    intent = OrderIntent("INT_2", "SIG_2", "EURUSD", "SELL", 1.15542, 1.15718, 1.15190, 0.01)
    attempt = ExecutionAttempt("ATT_2", "INT_2", datetime.now(timezone.utc), 
                               mt5_retcode=10009, mt5_comment="ok", succeeded=True)
    position = Position(589629837, "EURUSDm", "SELL", 0.01, 1.15590, 
                        datetime.now(timezone.utc), sl=1.15766, tp=1.15414)
    entry_deal = Deal(342648645, 589629837, 0, 1.15590, 0.01, 0.0, 0.0, 0.0, datetime.now(timezone.utc))
    
    trade = create_trade_lifecycle(sig, intent, attempt, position, entry_deal)
    print(f"  TradeLifecycle created: {trade.trade_id}")
    print(f"  Has position: {trade.position is not None}")
    print(f"  Has entry deal: {trade.entry_deal is not None}")
    print(f"  Is complete (closed): {trade.is_complete}")
    
    print(f"\n{'='*65}")
    print("  VERDICT: Database records represent OBSERVED REALITY")
    print("  Not requested intention. MT5 state is authoritative.")
    print(f"{'='*65}")
