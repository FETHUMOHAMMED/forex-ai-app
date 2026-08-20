"""Execution Gate - BLOCKS order, not logs exception.
Any gate failure = NO mt5.order_send() called. Period."""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone

@dataclass
class ExecutionGateResult:
    """Result of execution gate - BLOCKED or ALLOWED"""
    allowed: bool
    blocked_at: Optional[str] = None
    reason: Optional[str] = None

class ExecutionGate:
    """THE hard blocker before mt5.order_send().
    Each check returns False = BLOCKED. No exceptions logged and ignored.
    """
    
    def __init__(self):
        self.gate_order = [
            "FRESH", "ENTRY", "SL", "TP", "SPREAD", 
            "RISK", "SIZE", "ACCOUNT", "DUPLICATE", "MT5"
        ]
    
    def check(self, signal: dict, market: dict, account: dict, 
              existing_positions: list) -> ExecutionGateResult:
        """
        Run ALL gates in order. First failure = BLOCKED.
        Returns ExecutionGateResult. If allowed=False, DO NOT CALL order_send().
        """
        
        # GATE 1: FRESH
        signal_age = signal.get('age_seconds')
        if signal_age is None or signal_age > 120:
            return ExecutionGateResult(False, "FRESH", 
                                      f"Signal age {signal_age}s exceeds 120s")
        
        # GATE 2: ENTRY VALID
        entry = signal.get('entry')
        if entry is None or entry <= 0:
            return ExecutionGateResult(False, "ENTRY", "Invalid entry price")
        
        # GATE 3: SL VALID
        sl = signal.get('stop_loss')
        direction = signal.get('direction')
        current_entry = market.get('bid') if direction == 'SELL' else market.get('ask')
        if sl is None or current_entry is None:
            return ExecutionGateResult(False, "SL", "Missing SL or market price")
        if direction == 'SELL' and sl <= current_entry:
            return ExecutionGateResult(False, "SL", 
                                      f"SL {sl} below entry {current_entry} for SELL")
        if direction == 'BUY' and sl >= current_entry:
            return ExecutionGateResult(False, "SL",
                                      f"SL {sl} above entry {current_entry} for BUY")
        
        # GATE 4: TP VALID
        tp = signal.get('take_profit')
        if tp is None:
            return ExecutionGateResult(False, "TP", "Missing TP")
        if direction == 'SELL' and tp >= current_entry:
            return ExecutionGateResult(False, "TP",
                                      f"TP {tp} above entry {current_entry} for SELL")
        if direction == 'BUY' and tp <= current_entry:
            return ExecutionGateResult(False, "TP",
                                      f"TP {tp} below entry {current_entry} for BUY")
        
        # GATE 5: SPREAD VALID
        spread = market.get('spread', 0)
        if spread > 0.0015:
            return ExecutionGateResult(False, "SPREAD", f"Spread {spread} too wide")
        
        # GATE 6: SIZE VALID (check before risk - oversized volume blocks here)
        volume = signal.get("volume", 0.01)
        if volume > 0.01:
            return ExecutionGateResult(False, "SIZE", f"Volume {volume} exceeds 0.01 max")
        
        # GATE 7: RISK VALID
        risk_budget = account.get('equity', 0) * account.get('risk_pct', 0.0005)
        sl_pips = abs(current_entry - sl) / 0.0001
        actual_risk = sl_pips * 10.0 * volume
        if actual_risk > risk_budget * 1.01:
            return ExecutionGateResult(False, "RISK",
                                      f"Risk ${actual_risk:.2f} > budget ${risk_budget:.4f}")
        
        # GATE 8: ACCOUNT VALID
        if account.get('account_id') not in [REDACTED_LIVE_ACCOUNT, REDACTED_DEMO_ACCOUNT]:
            return ExecutionGateResult(False, "ACCOUNT",
                                      f"Invalid account {account.get('account_id')}")
        
        # GATE 9: DUPLICATE
        for pos in existing_positions:
            if pos.get('symbol') == signal.get('pair') and pos.get('direction') == direction:
                return ExecutionGateResult(False, "DUPLICATE",
                                          f"Already have {direction} on {signal.get('pair')}")
        
        # GATE 10: MT5 READY
        if not market.get('mt5_connected'):
            return ExecutionGateResult(False, "MT5", "MT5 not connected")
        
        # ALL GATES PASSED
        return ExecutionGateResult(True)


def execute_gate(signal: dict, market: dict, account: dict, positions: list) -> ExecutionGateResult:
    """
    THE function called before EVERY mt5.order_send().
    If result.allowed is False, the order is BLOCKED. No exception. No log-and-continue.
    """
    gate = ExecutionGate()
    result = gate.check(signal, market, account, positions)
    
    if not result.allowed:
        print(f"[EXECUTION BLOCKED] At gate: {result.blocked_at}")
        print(f"[EXECUTION BLOCKED] Reason: {result.reason}")
        print(f"[EXECUTION BLOCKED] mt5.order_send() NOT CALLED")
    
    return result


# ============================================================================
# TEST - Prove every gate blocks
# ============================================================================
if __name__ == "__main__":
    print("=" * 65)
    print("  EXECUTION GATE - HARD BLOCKER TEST")
    print("=" * 65)
    
    tests = [
        ("Stale signal", 
         {'age_seconds': 300, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
         {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
         {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
        ("Invalid SL (below entry for SELL)",
         {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15299, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
         {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
         {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
        ("Risk too high ($19 account)",
         {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
         {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
         {'equity': 19.06, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
        ("Duplicate position",
         {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
         {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
         {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT},
         [{'symbol': 'EURUSD', 'direction': 'SELL'}]),
        ("Valid signal ($5000 account)",
         {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
         {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
         {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
    ]
    
    for name, signal, market, account, positions in tests:
        result = execute_gate(signal, market, account, positions)
        icon = "ALLOWED" if result.allowed else "BLOCKED"
        gate_info = f" (at {result.blocked_at})" if result.blocked_at else ""
        print(f"\n  [{icon}] {name}{gate_info}")
        if result.reason:
            print(f"       {result.reason}")
    
    print(f"\n{'='*65}")
