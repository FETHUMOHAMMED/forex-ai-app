"""Verify Risk Gate - All 10 advisor items"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.risk.deep_health
from packages.integrity.registry import registry

# Advisor's 10 required risk checks
advisor_items = [
    ("RISK-001", "Equity available", "equity"),
    ("RISK-002", "Risk percentage available", "percentage"),
    ("RISK-003", "Monetary budget calculated", "budget"),
    ("RISK-004", "Entry available", "entry"),
    ("RISK-005", "SL available", "sl"),
    ("RISK-006", "Pip value available", "pip_value"),
    ("RISK-007", "Contract size available", "contract_size"),
    ("RISK-008", "Position size calculated", "position_size"),
    ("RISK-009", "Actual risk calculated", "actual"),
    ("RISK-010", "Actual risk <= budget", "within_budget"),
]

# Run all risk checks
risk_checks = {}
for fn in registry.get_all():
    result = fn()
    if result.domain == 'risk':
        risk_checks[result.check] = result

print("=" * 70)
print("  RISK GATE - ADVISOR 10 ITEM VERIFICATION")
print("=" * 70)

present = 0
passing = 0
for item_id, description, check_name in advisor_items:
    if check_name in risk_checks:
        present += 1
        result = risk_checks[check_name]
        icon = "PASS" if result.passed else "FAIL"
        if result.passed:
            passing += 1
        print(f"  [{icon}] {item_id}: {description}")
        print(f"       Check: {check_name}")
        print(f"       Detail: {result.detail}")
        print(f"       Severity: {result.severity.value}")
    else:
        print(f"  [MISSING] {item_id}: {description}")
        print(f"       Check: {check_name} NOT FOUND")
    print()

print(f"  {'='*55}")
print(f"  ITEMS PRESENT: {present}/10")
print(f"  ITEMS PASSING: {passing}/10")

# Show advisor's example
from packages.integrity.risk.deep_health import calculate_risk_evidence
evidence = calculate_risk_evidence(19.00, 0.0005, 1.15542, 1.15718, 0.01)

print(f"\n  ADVISOR EXAMPLE:")
print(f"    Equity: ${evidence.equity:.2f}")
print(f"    Budget: ${evidence.budget:.4f}")
print(f"    Actual Risk: ${evidence.actual_risk:.2f}")
print(f"    Risk Ratio: {evidence.risk_ratio:.2f}x")
print(f"    Result: {'HALT' if not evidence.is_safe else 'SAFE'}")
print(f"    Expected: HALT (185.26x)")

ratio_matches = abs(evidence.risk_ratio - 185.26) < 1.0
verify_example = not evidence.is_safe and ratio_matches

if present == 10 and verify_example:
    print(f"\n  VERDICT: RISK GATE COMPLETE - ALL 10 ITEMS + ADVISOR EXAMPLE VERIFIED")
elif present == 10:
    print(f"\n  VERDICT: ALL 10 ITEMS PRESENT (advisor example mismatch)")
else:
    print(f"\n  VERDICT: INCOMPLETE - {10 - present} items missing")
print("=" * 70)
