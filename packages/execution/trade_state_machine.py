"""Trade Execution State Machine - Enforces valid lifecycle transitions.
Invalid transitions like SIGNAL_CREATED -> CLOSED are IMPOSSIBLE.
"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict

class TradeState(str, Enum):
    """Explicit trade lifecycle states - NO shortcuts allowed"""
    SIGNAL_CREATED = "SIGNAL_CREATED"         # AI generated a signal
    RISK_APPROVED = "RISK_APPROVED"           # Risk gate passed
    RISK_REJECTED = "RISK_REJECTED"           # Risk gate blocked (terminal)
    ORDER_SUBMITTED = "ORDER_SUBMITTED"       # mt5.order_send() called
    ORDER_REJECTED = "ORDER_REJECTED"         # MT5 rejected order (terminal)
    ORDER_ACCEPTED = "ORDER_ACCEPTED"         # MT5 accepted order
    POSITION_OPENED = "POSITION_OPENED"       # Position exists in MT5
    POSITION_MODIFIED = "POSITION_MODIFIED"   # SL/TP modified
    POSITION_CLOSED = "POSITION_CLOSED"       # Position closed in MT5
    DEALS_RECONCILED = "DEALS_RECONCILED"     # DB matches MT5 deals
    TRADE_FINALIZED = "TRADE_FINALIZED"       # All data verified (terminal)
    
    @property
    def is_terminal(self) -> bool:
        return self in (TradeState.RISK_REJECTED, TradeState.ORDER_REJECTED, 
                        TradeState.TRADE_FINALIZED)
    
    @property 
    def is_active(self) -> bool:
        return self in (TradeState.ORDER_ACCEPTED, TradeState.POSITION_OPENED,
                        TradeState.POSITION_MODIFIED)

# ============================================================================
# VALID TRANSITIONS - The law. No exceptions.
# ============================================================================

VALID_TRANSITIONS: Dict[TradeState, List[TradeState]] = {
    TradeState.SIGNAL_CREATED:   [TradeState.RISK_APPROVED, TradeState.RISK_REJECTED],
    TradeState.RISK_APPROVED:    [TradeState.ORDER_SUBMITTED],
    TradeState.RISK_REJECTED:    [],  # Terminal
    TradeState.ORDER_SUBMITTED:  [TradeState.ORDER_ACCEPTED, TradeState.ORDER_REJECTED],
    TradeState.ORDER_REJECTED:   [],  # Terminal
    TradeState.ORDER_ACCEPTED:   [TradeState.POSITION_OPENED],
    TradeState.POSITION_OPENED:  [TradeState.POSITION_MODIFIED, TradeState.POSITION_CLOSED],
    TradeState.POSITION_MODIFIED:[TradeState.POSITION_MODIFIED, TradeState.POSITION_CLOSED],
    TradeState.POSITION_CLOSED:  [TradeState.DEALS_RECONCILED],
    TradeState.DEALS_RECONCILED: [TradeState.TRADE_FINALIZED],
    TradeState.TRADE_FINALIZED:  [],  # Terminal
}

# Forbidden transitions (explicitly blocked)
FORBIDDEN_TRANSITIONS = [
    (TradeState.SIGNAL_CREATED, TradeState.POSITION_CLOSED),   # Can't skip to closed
    (TradeState.SIGNAL_CREATED, TradeState.TRADE_FINALIZED),   # Can't skip to finalized
    (TradeState.RISK_APPROVED, TradeState.POSITION_CLOSED),    # Must go through order
    (TradeState.ORDER_ACCEPTED, TradeState.TRADE_FINALIZED),   # Must reconcile first
    (TradeState.POSITION_OPENED, TradeState.TRADE_FINALIZED),  # Must close first
]

# ============================================================================
# STATE MACHINE
# ============================================================================

class InvalidTransitionError(Exception):
    def __init__(self, from_state: TradeState, to_state: TradeState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"INVALID TRANSITION: {from_state.value} -> {to_state.value}. "
            f"Valid transitions from {from_state.value}: "
            f"{[s.value for s in VALID_TRANSITIONS.get(from_state, [])]}"
        )

@dataclass
class TradeStateMachine:
    """Manages trade lifecycle with enforced state transitions.
    
    Usage:
        tsm = TradeStateMachine(trade_id="V3_001")
        tsm.transition_to(TradeState.RISK_APPROVED)  # OK
        tsm.transition_to(TradeState.POSITION_CLOSED) # Raises InvalidTransitionError!
    """
    trade_id: str
    current_state: TradeState = TradeState.SIGNAL_CREATED
    state_history: List[tuple] = field(default_factory=list)
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def transition_to(self, new_state: TradeState, metadata: Optional[dict] = None) -> 'TradeStateMachine':
        """Attempt to transition to a new state. Raises on invalid transition."""
        
        # Check if transition is explicitly forbidden
        if (self.current_state, new_state) in FORBIDDEN_TRANSITIONS:
            raise InvalidTransitionError(self.current_state, new_state)
        
        # Check if transition is in valid list
        if new_state not in VALID_TRANSITIONS.get(self.current_state, []):
            raise InvalidTransitionError(self.current_state, new_state)
        
        # Check not transitioning from terminal state
        if self.current_state.is_terminal:
            raise InvalidTransitionError(self.current_state, new_state)
        
        # Record transition
        transition = (
            self.current_state,
            new_state,
            datetime.now(timezone.utc),
            metadata or {}
        )
        self.state_history.append(transition)
        self.current_state = new_state
        
        return self
    
    def can_transition_to(self, new_state: TradeState) -> bool:
        """Check if transition is valid without raising"""
        try:
            return new_state in VALID_TRANSITIONS.get(self.current_state, []) and not self.current_state.is_terminal
        except:
            return False
    
    @property
    def is_complete(self) -> bool:
        return self.current_state == TradeState.TRADE_FINALIZED
    
    @property
    def is_active(self) -> bool:
        return self.current_state.is_active
    
    def lifecycle_summary(self) -> str:
        """Human-readable lifecycle summary"""
        lines = [f"Trade: {self.trade_id}"]
        lines.append(f"Current State: {self.current_state.value}")
        lines.append(f"Created: {self.created_at_utc.isoformat()}")
        lines.append("Transitions:")
        for from_s, to_s, ts, meta in self.state_history:
            lines.append(f"  {from_s.value} -> {to_s.value} at {ts.isoformat()}")
            if meta:
                lines.append(f"    metadata: {meta}")
        return "\n".join(lines)


# ============================================================================
# QUICK STATE MACHINE TEST
# ============================================================================

def test_state_machine():
    """Verify valid transitions work and invalid ones raise errors"""
    tsm = TradeStateMachine("test_001")
    
    # Valid path
    tsm.transition_to(TradeState.RISK_APPROVED)
    tsm.transition_to(TradeState.ORDER_SUBMITTED)
    tsm.transition_to(TradeState.ORDER_ACCEPTED)
    tsm.transition_to(TradeState.POSITION_OPENED)
    tsm.transition_to(TradeState.POSITION_CLOSED)
    tsm.transition_to(TradeState.DEALS_RECONCILED)
    tsm.transition_to(TradeState.TRADE_FINALIZED)
    
    assert tsm.is_complete, "Should be complete"
    print("Valid path: OK")
    
    # Invalid: skip from SIGNAL to CLOSED
    tsm2 = TradeStateMachine("test_002")
    try:
        tsm2.transition_to(TradeState.POSITION_CLOSED)
        assert False, "Should have raised"
    except InvalidTransitionError as e:
        print(f"Invalid path blocked: {e}")
    
    # Invalid: from terminal state
    tsm3 = TradeStateMachine("test_003")
    tsm3.transition_to(TradeState.RISK_REJECTED)
    try:
        tsm3.transition_to(TradeState.ORDER_SUBMITTED)
        assert False, "Should have raised"
    except InvalidTransitionError as e:
        print(f"Terminal state blocked: {e}")
    
    print("\nAll state machine tests passed!")

if __name__ == "__main__":
    test_state_machine()
