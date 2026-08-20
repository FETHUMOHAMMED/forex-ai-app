"""Trade State Hierarchy - RAW ? EXECUTION_VALID ? QUALIFIED."""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict

class TradeStatus(str, Enum):
    """The complete trade lifecycle states."""
    # Initial
    SIGNAL = "SIGNAL"
    
    # Execution attempt
    ORDER_ATTEMPT = "ORDER_ATTEMPT"
    EXECUTED = "EXECUTED"
    
    # Rejection states
    STALE = "STALE"
    INVALID_SL = "INVALID_SL"
    INVALID_TP = "INVALID_TP"
    SPREAD_EXCEEDED = "SPREAD_EXCEEDED"
    RISK_EXCEEDED = "RISK_EXCEEDED"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    DUPLICATE_REJECTED = "DUPLICATE_REJECTED"
    
    # Execution exceptions
    EXECUTION_EXCEPTION = "EXECUTION_EXCEPTION"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"
    PHANTOM = "PHANTOM"
    
    # Completion
    CLOSED = "CLOSED"
    RECONCILED = "RECONCILED"
    QUALIFIED = "QUALIFIED"

class TradeClassification(str, Enum):
    """Three-level classification."""
    RAW = "RAW"                          # Something was recorded
    EXECUTION_VALID = "EXECUTION_VALID"  # Followed execution contract
    QUALIFIED = "QUALIFIED"              # Valid + eligible for strategy stats

@dataclass
class TradeStateMachine:
    """Full trade state hierarchy."""
    trade_id: str
    status: TradeStatus = TradeStatus.SIGNAL
    classification: TradeClassification = TradeClassification.RAW
    status_history: List[tuple] = None
    
    def __post_init__(self):
        if self.status_history is None:
            self.status_history = []
    
    def transition(self, new_status: TradeStatus, reason: str = ""):
        """Transition trade to new status."""
        self.status_history.append({
            "from": self.status.value,
            "to": new_status.value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.status = new_status
        self._update_classification(new_status)
    
    def _update_classification(self, status: TradeStatus):
        """Update classification based on status."""
        if status in (TradeStatus.QUALIFIED,):
            self.classification = TradeClassification.QUALIFIED
        elif status in (TradeStatus.RECONCILED,):
            self.classification = TradeClassification.EXECUTION_VALID
        else:
            self.classification = TradeClassification.RAW
    
    def is_qualified(self) -> bool:
        return self.classification == TradeClassification.QUALIFIED
    
    def is_execution_valid(self) -> bool:
        return self.classification in (TradeClassification.EXECUTION_VALID, TradeClassification.QUALIFIED)
    
    def print_state(self):
        """Print complete state."""
        print(f"  Trade: {self.trade_id}")
        print(f"  Status: {self.status.value}")
        print(f"  Classification: {self.classification.value}")
        print(f"  History: {len(self.status_history)} transitions")
        for h in self.status_history:
            print(f"    {h['from']} -> {h['to']} ({h['reason']})")


def classify_trade(execution_valid: bool, reconciliation_passed: bool, 
                   strategy_eligible: bool) -> TradeClassification:
    """
    THE classification function.
    RAW: anything recorded
    EXECUTION_VALID: passed execution contract + reconciled
    QUALIFIED: execution valid + eligible for strategy stats
    """
    if strategy_eligible and execution_valid and reconciliation_passed:
        return TradeClassification.QUALIFIED
    elif execution_valid and reconciliation_passed:
        return TradeClassification.EXECUTION_VALID
    else:
        return TradeClassification.RAW


if __name__ == "__main__":
    print("=" * 70)
    print("  TRADE STATE HIERARCHY")
    print("=" * 70)
    
    # Test 1: Perfect trade
    print("\n  TEST 1: Perfect qualified trade")
    t1 = TradeStateMachine("PERFECT_001")
    t1.transition(TradeStatus.ORDER_ATTEMPT, "Signal approved")
    t1.transition(TradeStatus.EXECUTED, "Filled @ 1.15542")
    t1.transition(TradeStatus.CLOSED, "Position closed")
    t1.transition(TradeStatus.RECONCILED, "PnL matched")
    t1.transition(TradeStatus.QUALIFIED, "All 14 checks passed")
    t1.print_state()
    
    # Test 2: Stale signal
    print("\n  TEST 2: Stale signal rejected")
    t2 = TradeStateMachine("STALE_001")
    t2.transition(TradeStatus.SIGNAL, "Signal generated")
    t2.transition(TradeStatus.STALE, "300s old > 120s max")
    t2.print_state()
    
    # Test 3: ID 163 scenario
    print("\n  TEST 3: ID 163 (invalid SL)")
    t3 = TradeStateMachine("ID_163")
    t3.transition(TradeStatus.SIGNAL, "Signal: SELL EURUSD")
    t3.transition(TradeStatus.ORDER_ATTEMPT, "Attempted execution")
    t3.transition(TradeStatus.EXECUTED, "Filled @ 1.15542")
    t3.transition(TradeStatus.EXECUTION_EXCEPTION, "Invalid SL: below entry for SELL")
    t3.print_state()
    
    # Test 4: Phantom
    print("\n  TEST 4: Phantom trade")
    t4 = TradeStateMachine("PHANTOM_001")
    t4.transition(TradeStatus.PHANTOM, "No MT5 position found")
    t4.print_state()
    
    print(f"\n{'='*70}")
    print("  CLASSIFICATION RULES:")
    print("  RAW:           Any recorded trade")
    print("  EXECUTION_VALID: Passed contract + reconciled")
    print("  QUALIFIED:     Valid + strategy eligible")
    print("=" * 70)
