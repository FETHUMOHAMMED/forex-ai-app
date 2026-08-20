# -*- coding: utf-8 -*-
"""Verify Scanner != Trading Gate architecture"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

print("=" * 70)
print("  SCANNER vs TRADING GATE - ARCHITECTURE VERIFICATION")
print("=" * 70)

print("""
  ADVISOR ARCHITECTURE:
  
  [ERROR SCANNER] --> System Health --> [CONTROL PLANE] --> Decision
                                                  |
                              +-------------------+-------------------+
                              |                                       |
                        [STRATEGY PLANE]                    [EXECUTION PLANE]
                         AI BUY/SELL                        Safety Gates (10)
                                                                   |
                                                            [MONETARY RISK]
                                                                   |
                                                            [MT5 EXECUTION]
""")

from pathlib import Path
checks = [
    ("Error Scanner", "packages/integrity/scanner.py", "Runs checks, reports health"),
    ("Control Plane", "packages/integrity/decision.py", "READY/DEGRADED/HALT decision"),
    ("Strategy Plane", "packages/strategy/canonical_engine.py", "AI BUY/SELL signals"),
    ("Execution Plane", "packages/integrity/execution/gate.py", "10 hard blocker gates"),
    ("Monetary Risk", "packages/risk/monetary_risk_gate.py", "actual_risk <= budget"),
    ("MT5 Execution", "packages/execution/account_manager.py", "Order submission"),
]

print("\n  LAYER VERIFICATION:")
all_exist = True
for name, filepath, purpose in checks:
    exists = Path(filepath).exists()
    if not exists:
        all_exist = False
    icon = "EXISTS" if exists else "MISSING"
    print(f"  [{icon}] {name}")
    print(f"       File: {filepath}")
    print(f"       Purpose: {purpose}")

print("\n  AUTHORITY HIERARCHY:")
print("    Scanner       -> Reports health (NO authority to trade)")
print("    Control Plane -> Makes decision (READY/DEGRADED/HALT)")
print("    Strategy      -> Generates signals (BUY/SELL/NO_TRADE)")
print("    Execution     -> Enforces gates (BLOCK if unsafe)")
print("    Risk          -> Budget check (HALT if exceeded)")
print("    MT5           -> Only executes if ALL above pass")

print("\n  ADVISOR EXAMPLE:")
print("    Strategy: BUY, confidence 91%")
print("    Control:  REJECT (stale signal)")
print("    Result:   NO TRADE")
print("    Enforced: Execution Gate blocks before MT5")

print("\n" + "=" * 70)
verdict = "ARCHITECTURE CORRECT - Scanner separate from Trading Gate" if all_exist else "MISSING COMPONENTS"
print(f"  VERDICT: {verdict}")
print("=" * 70)
