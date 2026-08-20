"""Verify Execution Gate - ALL 10 advisor gates in EXACT order"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.integrity.execution.gate import ExecutionGate, ExecutionGateResult, execute_gate

print("=" * 70)
print("  EXECUTION GATE - 10 GATE VERIFICATION")
print("=" * 70)

# The 10 gates in EXACT advisor order
advisor_gates = [
    "FRESH",
    "ENTRY", 
    "SL",
    "TP",
    "SPREAD",
    "RISK",
    "SIZE",
    "ACCOUNT",
    "DUPLICATE",
    "MT5",
]

# Check gate order is correct
gate = ExecutionGate()
gate_order_match = gate.gate_order == advisor_gates
print(f"\n  GATE ORDER:")
for i, g in enumerate(gate.gate_order, 1):
    expected = advisor_gates[i-1]
    match = "OK" if g == expected else "WRONG ORDER!"
    print(f"    {i:2}. {g} {'(' + match + ')' if match != 'OK' else ''}")

print(f"\n  Order Correct: {gate_order_match}")

# Test each gate BLOCKS independently
print(f"\n  BLOCKING TESTS:")

test_cases = [
    ("FRESH", "Stale signal (300s)", 
     {'age_seconds': 300, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
    
    ("ENTRY", "Invalid entry (None)",
     {'age_seconds': 10, 'entry': None, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
    
    ("SL", "SL below entry for SELL",
     {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15299, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
    
    ("TP", "TP above entry for SELL",
     {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.16000, 'direction': 'SELL', 'pair': 'EURUSD'},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
    
    ("SPREAD", "Spread too wide",
     {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
     {'bid': 1.15542, 'ask': 1.15742, 'spread': 0.002, 'mt5_connected': True},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
    
    ("RISK", "Risk exceeds budget",
     {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
     {'equity': 19.06, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
    
    ("SIZE", "Volume too large (tested via volume=1.0)",
     {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD', 'volume': 1.0},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
     
    ("ACCOUNT", "Invalid account",
     {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': 999999}, []),
    
    ("DUPLICATE", "Already have position",
     {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT},
     [{'symbol': 'EURUSD', 'direction': 'SELL'}]),
    
    ("MT5", "MT5 disconnected",
     {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': False},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),
]

all_blocked = True
for gate_name, description, signal, market, account, positions in test_cases:
    result = execute_gate(signal, market, account, positions)
    blocked_at_correct = not result.allowed and result.blocked_at == gate_name
    icon = "PASS" if blocked_at_correct else "FAIL"
    if not blocked_at_correct:
        all_blocked = False
    actual = f"blocked at {result.blocked_at}" if not result.allowed else "ALLOWED (should block!)"
    print(f"  [{icon}] {gate_name}: {description}")
    print(f"       Expected: blocked at {gate_name}")
    print(f"       Actual: {actual}")

print(f"\n  All 10 gates block correctly: {all_blocked}")

# Test valid signal passes
print(f"\n  VALID SIGNAL TEST:")
valid_result = execute_gate(
    {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
    {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
    {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []
)
print(f"  Valid signal: {'ALLOWED' if valid_result.allowed else 'BLOCKED (wrong!)'}")

print(f"\n{'='*70}")
print(f"  VERDICT: {'ALL 10 GATES WORK AS HARD BLOCKERS' if all_blocked and valid_result.allowed else 'ISSUES FOUND'}")
print(f"{'='*70}")
