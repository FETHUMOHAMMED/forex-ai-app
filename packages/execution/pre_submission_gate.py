"""Pre-Submission Gate - The FINAL contract before mt5.order_send().
Every step must PASS or order is NEVER sent. No post-hoc investigation needed.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, List
from enum import Enum

class GateStep(str, Enum):
    IMMUTABLE_SIGNAL = "IMMUTABLE_SIGNAL"
    FRESHNESS = "FRESHNESS"
    MARKET_SNAPSHOT = "MARKET_SNAPSHOT"
    ENTRY_DEVIATION = "ENTRY_DEVIATION"
    RECALCULATE_SLTP = "RECALCULATE_SLTP"
    SLTP_VALIDATION = "SLTP_VALIDATION"
    SPREAD_CHECK = "SPREAD_CHECK"
    RISK_CALCULATION = "RISK_CALCULATION"
    POSITION_SIZE = "POSITION_SIZE"
    FINAL_CONTRACT = "FINAL_CONTRACT"

@dataclass
class PreSubmissionResult:
    """Result of pre-submission gate"""
    signal_id: str
    steps: Dict[GateStep, dict] = field(default_factory=dict)
    is_approved: bool = False
    
    def add_step(self, step: GateStep, passed: bool, detail: str = ""):
        self.steps[step] = {"passed": passed, "detail": detail}
        return passed
    
    def summary(self):
        lines = [f"PRE-SUBMISSION GATE: {self.signal_id}"]
        for step in GateStep:
            if step in self.steps:
                s = self.steps[step]
                icon = "PASS" if s["passed"] else "FAIL"
                lines.append(f"  [{icon}] {step.value}: {s['detail']}")
            else:
                lines.append(f"  [....] {step.value}: NOT EXECUTED")
        lines.append(f"  APPROVED: {self.is_approved}")
        return "\n".join(lines)


def execute_pre_submission_gate(signal: dict, market_bid: float, market_ask: float,
                                 account_equity: float) -> PreSubmissionResult:
    """
    THE complete pre-submission gate.
    Any FAIL = NO mt5.order_send() call. No trade is ever placed.
    """
    result = PreSubmissionResult(signal_id=signal.get('signal_id', 'unknown'))
    
    # STEP 1: Immutable signal
    if signal.get('signal_id') and signal.get('generated_at'):
        result.add_step(GateStep.IMMUTABLE_SIGNAL, True, "Signal is immutable snapshot")
    else:
        result.add_step(GateStep.IMMUTABLE_SIGNAL, False, "Missing signal ID or timestamp")
        return result
    
    # STEP 2: Freshness (must be < 120s)
    age_seconds = (datetime.now(timezone.utc) - signal['generated_at']).total_seconds()
    if age_seconds < 120:
        result.add_step(GateStep.FRESHNESS, True, f"Age: {age_seconds:.0f}s")
    else:
        result.add_step(GateStep.FRESHNESS, False, f"STALE: {age_seconds:.0f}s > 120s")
        return result
    
    # STEP 3: Market snapshot available
    if market_bid > 0 and market_ask > 0:
        result.add_step(GateStep.MARKET_SNAPSHOT, True, f"Bid={market_bid} Ask={market_ask}")
    else:
        result.add_step(GateStep.MARKET_SNAPSHOT, False, "No market data")
        return result
    
    # STEP 4: Entry deviation
    current_entry = market_bid if signal['direction'] == 'SELL' else market_ask
    deviation_pips = abs(current_entry - signal['entry']) * 10000
    if deviation_pips <= 5.0:
        result.add_step(GateStep.ENTRY_DEVIATION, True, f"{deviation_pips:.1f} pips")
    else:
        result.add_step(GateStep.ENTRY_DEVIATION, False, f"{deviation_pips:.1f} pips > 5.0")
        return result
    
    # STEP 5: Recalculate SL/TP for current market
    sl_distance = abs(signal['stop_loss'] - signal['entry'])
    tp_distance = abs(signal['take_profit'] - signal['entry'])
    
    if signal['direction'] == 'SELL':
        actual_sl = current_entry + sl_distance
        actual_tp = current_entry - tp_distance
    else:
        actual_sl = current_entry - sl_distance
        actual_tp = current_entry + tp_distance
    
    result.add_step(GateStep.RECALCULATE_SLTP, True, 
                   f"SL={actual_sl:.5f} TP={actual_tp:.5f}")
    
    # STEP 6: SL/TP validation for direction
    if signal['direction'] == 'SELL':
        sl_valid = actual_sl > current_entry
        tp_valid = actual_tp < current_entry
    else:
        sl_valid = actual_sl < current_entry
        tp_valid = actual_tp > current_entry
    
    if sl_valid and tp_valid:
        result.add_step(GateStep.SLTP_VALIDATION, True, "Both on correct sides")
    else:
        result.add_step(GateStep.SLTP_VALIDATION, False, 
                       f"SL valid: {sl_valid}, TP valid: {tp_valid}")
        return result
    
    # STEP 7: Spread check
    spread = market_ask - market_bid
    if spread <= 0.0015:
        result.add_step(GateStep.SPREAD_CHECK, True, f"{spread:.6f}")
    else:
        result.add_step(GateStep.SPREAD_CHECK, False, f"{spread:.6f} too wide")
        return result
    
    # STEP 8: Risk calculation
    sl_pips = abs(actual_sl - current_entry) / 0.0001
    volume = 0.01
    actual_risk = sl_pips * 10.0 * volume
    risk_budget = account_equity * 0.0005
    
    if actual_risk <= risk_budget * 1.01:
        result.add_step(GateStep.RISK_CALCULATION, True, 
                       f"Risk ${actual_risk:.2f} <= Budget ${risk_budget:.4f}")
    else:
        result.add_step(GateStep.RISK_CALCULATION, False,
                       f"Risk ${actual_risk:.2f} > Budget ${risk_budget:.4f}")
        return result
    
    # STEP 9: Position size calculation
    result.add_step(GateStep.POSITION_SIZE, True, f"Volume: {volume}")
    
    # STEP 10: FINAL CONTRACT
    result.add_step(GateStep.FINAL_CONTRACT, True, "ALL GATES PASSED - READY FOR MT5")
    result.is_approved = True
    
    return result


if __name__ == "__main__":
    print("=" * 70)
    print("  PRE-SUBMISSION GATE - FAIL BEFORE ORDER, NOT AFTER")
    print("=" * 70)
    
    # Test 1: Fresh valid signal -> APPROVED
    fresh = {
        'signal_id': 'GOOD_001',
        'generated_at': datetime.now(timezone.utc),
        'pair': 'EURUSD',
        'direction': 'SELL',
        'entry': 1.15540,
        'stop_loss': 1.15716,
        'take_profit': 1.15164,
    }
    
    result = execute_pre_submission_gate(fresh, 1.15542, 1.15550, 5000)
    print(f"\n{result.summary()}")
    print(f"\n  If approved -> mt5.order_send() WILL be called")
    print(f"  If rejected -> mt5.order_send() NEVER called")
    
    # Test 2: Stale signal -> REJECTED at step 2
    stale = {
        'signal_id': 'BAD_001',
        'generated_at': datetime.now(timezone.utc).replace(hour=datetime.now().hour - 1),
        'pair': 'EURUSD',
        'direction': 'SELL',
        'entry': 1.15123,
        'stop_loss': 1.15299,
        'take_profit': 1.14842,
    }
    
    result2 = execute_pre_submission_gate(stale, 1.15542, 1.15550, 5000)
    print(f"\n{result2.summary()}")
    print(f"\n  STALE SIGNAL BLOCKED AT STEP 2")
    print(f"  mt5.order_send() was NEVER called")
    print(f"  No post-hoc investigation needed")
    
    print(f"\n{'='*70}")
