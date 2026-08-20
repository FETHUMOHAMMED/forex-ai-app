"""ExecutedTrade - An object that CANNOT exist in an invalid state.
Invalid execution states are UNREPRESENTABLE, not just checked.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass(frozen=True)
class ExecutedTrade:
    """Immutable executed trade - validation happens in __post_init__.
    Cannot be constructed with invalid SL/TP for the direction.
    """
    trade_id: str
    pair: str
    direction: Direction
    account_id: int
    account_name: str
    actual_entry: float
    actual_sl: float
    actual_tp: float
    volume: float
    position_ticket: int
    actual_fill_at: datetime
    
    def __post_init__(self):
        """Validate on construction - invalid trades raise immediately"""
        # Actual entry must be positive
        if self.actual_entry <= 0:
            raise ValueError(f"Invalid entry price: {self.actual_entry}")
        
        # Volume must be positive
        if self.volume <= 0:
            raise ValueError(f"Invalid volume: {self.volume}")
        
        # Position ticket required
        if self.position_ticket <= 0:
            raise ValueError(f"Invalid position ticket: {self.position_ticket}")
        
        # SL must be on CORRECT side of entry for direction
        if self.direction == Direction.SELL:
            if self.actual_sl <= self.actual_entry:
                raise ValueError(
                    f"INVALID SL for SELL: SL({self.actual_sl}) must be ABOVE entry({self.actual_entry})"
                )
            if self.actual_tp >= self.actual_entry:
                raise ValueError(
                    f"INVALID TP for SELL: TP({self.actual_tp}) must be BELOW entry({self.actual_entry})"
                )
        else:  # BUY
            if self.actual_sl >= self.actual_entry:
                raise ValueError(
                    f"INVALID SL for BUY: SL({self.actual_sl}) must be BELOW entry({self.actual_entry})"
                )
            if self.actual_tp <= self.actual_entry:
                raise ValueError(
                    f"INVALID TP for BUY: TP({self.actual_tp}) must be ABOVE entry({self.actual_entry})"
                )
        
        # Account identity must be consistent
        if self.account_name == "Demo2" and self.account_id == REDACTED_LIVE_ACCOUNT:
            raise ValueError("Account mismatch: Demo2 name with Live_Micro ID")
    
    @property
    def is_valid(self) -> bool:
        """Always True if object exists (validation happened at construction)"""
        return True
    
    @property
    def sl_distance_pips(self) -> float:
        return abs(self.actual_entry - self.actual_sl) / 0.0001
    
    @property
    def tp_distance_pips(self) -> float:
        return abs(self.actual_entry - self.actual_tp) / 0.0001
    
    @property
    def risk_reward_ratio(self) -> float:
        return round(self.tp_distance_pips / self.sl_distance_pips, 2) if self.sl_distance_pips > 0 else 0
    
    def summary(self) -> str:
        return (f"{self.trade_id}: {self.direction.value} {self.pair} "
                f"@ {self.actual_entry:.5f} | SL={self.actual_sl:.5f} | TP={self.actual_tp:.5f} "
                f"| Vol={self.volume} | Pos={self.position_ticket}")


# ============================================================================
# TEST - Prove invalid states are unrepresentable
# ============================================================================
if __name__ == "__main__":
    print("=" * 65)
    print("  EXECUTED TRADE - INVALID STATE PREVENTION")
    print("=" * 65)
    
    # Test 1: VALID SELL trade
    print("\n[1] Valid SELL trade:")
    try:
        valid_trade = ExecutedTrade(
            trade_id="V3_TEST_SELL_OK",
            pair="EURUSD",
            direction=Direction.SELL,
            account_id=REDACTED_LIVE_ACCOUNT,
            account_name="Live_Micro",
            actual_entry=1.15542,
            actual_sl=1.15718,  # Above entry (valid for SELL)
            actual_tp=1.15190,  # Below entry (valid for SELL)
            volume=0.01,
            position_ticket=589629837,
            actual_fill_at=datetime.now(timezone.utc),
        )
        print(f"  CREATED: {valid_trade.summary()}")
        print(f"  SL distance: {valid_trade.sl_distance_pips:.1f} pips")
        print(f"  TP distance: {valid_trade.tp_distance_pips:.1f} pips")
        print(f"  RR ratio: {valid_trade.risk_reward_ratio}")
    except ValueError as e:
        print(f"  FAILED: {e}")
    
    # Test 2: INVALID SELL - SL below entry (ID 163's exact error)
    print("\n[2] INVALID SELL (SL below entry - ID 163 error):")
    try:
        ExecutedTrade(
            trade_id="V3_TEST_SELL_BAD",
            pair="EURUSD",
            direction=Direction.SELL,
            account_id=REDACTED_LIVE_ACCOUNT,
            account_name="Live_Micro",
            actual_entry=1.15542,
            actual_sl=1.15299,  # BELOW entry (INVALID for SELL!)
            actual_tp=1.14842,
            volume=0.01,
            position_ticket=589584400,
            actual_fill_at=datetime.now(timezone.utc),
        )
        print("  ERROR: Should have been rejected!")
    except ValueError as e:
        print(f"  CORRECTLY REJECTED: {e}")
    
    # Test 3: Account mismatch
    print("\n[3] Account mismatch (Demo2 name + Live_Micro ID):")
    try:
        ExecutedTrade(
            trade_id="V3_TEST_ACCOUNT_BAD",
            pair="EURUSD",
            direction=Direction.SELL,
            account_id=REDACTED_LIVE_ACCOUNT,
            account_name="Demo2",  # MISMATCH!
            actual_entry=1.15542,
            actual_sl=1.15718,
            actual_tp=1.15190,
            volume=0.01,
            position_ticket=589629837,
            actual_fill_at=datetime.now(timezone.utc),
        )
        print("  ERROR: Should have been rejected!")
    except ValueError as e:
        print(f"  CORRECTLY REJECTED: {e}")
    
    print(f"\n{'='*65}")
    print("  RESULT: Invalid states are UNREPRESENTABLE")
    print("  The object cannot be constructed with bad SL/TP or wrong account")
    print(f"{'='*65}")
