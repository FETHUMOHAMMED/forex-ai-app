"""Verify 8-Level Gate Hierarchy - All advisor requirements"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.integrity.gate_hierarchy import GateHierarchy, GateLevel, GateResult

print("=" * 70)
print("  GATE HIERARCHY - ADVISOR VERIFICATION")
print("=" * 70)

# Advisor's required 8 gates
required_gates = [
    (GateLevel.GATE_0, "SYSTEM INTEGRITY", "NO TRADE"),
    (GateLevel.GATE_1, "DATA INTEGRITY", "NO TRADE"),
    (GateLevel.GATE_2, "SIGNAL INTEGRITY", "NO TRADE"),
    (GateLevel.GATE_3, "EXECUTION CONTRACT", "NO TRADE"),
    (GateLevel.GATE_4, "RISK", "NO TRADE"),
    (GateLevel.GATE_5, "MT5", "NO TRADE"),
    (GateLevel.GATE_6, "TRADE QUALIFICATION", "EXCLUDE_FROM_RESEARCH"),
    (GateLevel.GATE_7, "STRATEGY VALIDATION", "VALIDATION_ONLY"),
]

print("\n  GATE STRUCTURE CHECK:")
all_gates_present = True
for gate, name, action in required_gates:
    # Check if gate check method exists
    gate_num = gate.value.replace("GATE_", "")
    method_name = f"check_gate_{gate_num}"
    if hasattr(GateHierarchy, method_name):
        icon = "EXISTS"
    else:
        icon = "MISSING"
        all_gates_present = False
    print(f"  [{icon}] {gate.value}: {name}")
    print(f"       Action if fail: {action}")

print(f"\n  TEST: Gate 4 (RISK) failure should BLOCK trading")
hierarchy = GateHierarchy()
result = hierarchy.run_all(
    domains={"api": "PASS", "database": "PASS", "mt5": "PASS", "ai": "PASS",
             "frontend": "PASS", "observability": "PASS"},
    data={"account_ok": True, "timestamps_ok": True, "provenance_ok": True,
          "schema_ok": True, "identity_ok": True},
    signal={"fresh": True, "features_valid": True, "confidence_valid": True,
            "signal_valid": True},
    execution={"entry_valid": True, "deviation_ok": True, "sl_valid": True,
               "tp_valid": True, "spread_ok": True},
    risk={"equity_ok": False, "budget_ok": False, "sizing_ok": False,
          "exposure_ok": True, "correlation_ok": True},
    mt5={"account_match": True, "position_verified": True,
         "order_verified": True, "reconciled": True},
    trade={"closed": False, "pnl_valid": False, "contract_valid": False,
           "reconciled": False},
    trades_count=0, has_oos=False, has_walkforward=False,
)

print(f"\n  TRADING ALLOWED: {result['trading_allowed']}")
print(f"  Expected: False (Gate 4 RISK fails)")
risk_blocked = not result['trading_allowed']

# Verify each gate result
print(f"\n  GATE RESULTS:")
gate_pass_fail = []
for gate in GateLevel:
    passed = result['gate_results'].get(gate.value)
    gate_pass_fail.append(passed)
    icon = "PASS" if passed else "FAIL"
    print(f"    {icon} {gate.value}: {passed}")

# Verify Gate 0-3 pass, Gate 4 fails, Gate 5 passes
gates_correct = (
    result['gate_results'].get(GateLevel.GATE_0.value) == True and
    result['gate_results'].get(GateLevel.GATE_1.value) == True and
    result['gate_results'].get(GateLevel.GATE_2.value) == True and
    result['gate_results'].get(GateLevel.GATE_3.value) == True and
    result['gate_results'].get(GateLevel.GATE_4.value) == False and  # RISK fails
    result['gate_results'].get(GateLevel.GATE_5.value) == True
)

print(f"\n  GATE SEQUENCE CORRECT: {gates_correct}")
print(f"  (Gates 0-3 pass, Gate 4 RISK fails, Gate 5 passes)")

# Verify Gate 6 fails ? excluded, Gate 7 fails ? validation only
gate6_fails = result['gate_results'].get(GateLevel.GATE_6.value) == False
gate7_fails = result['gate_results'].get(GateLevel.GATE_7.value) == False
print(f"  Gate 6 fails ? EXCLUDE_FROM_RESEARCH: {gate6_fails}")
print(f"  Gate 7 fails ? VALIDATION_ONLY: {gate7_fails}")

print(f"\n{'='*70}")
checks = [all_gates_present, risk_blocked, gates_correct, gate6_fails, gate7_fails]
passed_count = sum(checks)
print(f"  RESULT: {passed_count}/{len(checks)} TESTS PASSED")
if passed_count == len(checks):
    print(f"  VERDICT: 8-LEVEL GATE HIERARCHY COMPLETE")
    print(f"    - All 8 gates present")
    print(f"    - Risk failure blocks trading")
    print(f"    - Gate sequence correct")
    print(f"    - Gate 6 excludes from research")
    print(f"    - Gate 7 keeps validation-only")
print("=" * 70)
