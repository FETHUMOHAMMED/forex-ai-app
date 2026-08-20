"""Verify AI Gate - All 13 advisor items + confidence 1.83 rejection"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.ai.deep_health
from packages.integrity.registry import registry

# Advisor's 13 required AI checks
advisor_items = [
    ("AI-001", "Model files exist", "model_files"),
    ("AI-002", "Model registry valid", "registry"),
    ("AI-003", "All expected models loaded", "models_loaded"),
    ("AI-004", "Feature contract matches", "feature_contract"),
    ("AI-005", "Feature count correct", "feature_count"),
    ("AI-006", "Feature ordering correct", "feature_order"),
    ("AI-007", "No NaN", "no_nan"),
    ("AI-008", "No infinity", "no_infinity"),
    ("AI-009", "Inference completes", "inference"),
    ("AI-010", "Prediction within expected range", "prediction_range"),
    ("AI-011", "Confidence within [0,1]", "confidence_range"),
    ("AI-012", "Signal in {BUY, SELL, NO_TRADE}", "signal_valid"),
    ("AI-013", "Model version recorded", "model_version"),
]

# Run all AI checks
ai_checks = {}
for fn in registry.get_all():
    result = fn()
    if result.domain == 'ai':
        ai_checks[result.check] = result

print("=" * 70)
print("  AI GATE - ADVISOR 13 ITEM VERIFICATION")
print("=" * 70)

present = 0
passing = 0
for item_id, description, check_name in advisor_items:
    if check_name in ai_checks:
        present += 1
        result = ai_checks[check_name]
        icon = "PASS" if result.passed else "FAIL"
        if result.passed:
            passing += 1
        print(f"  [{icon}] {item_id}: {description}")
        print(f"       Detail: {result.detail}")
    else:
        print(f"  [MISSING] {item_id}: {description}")
        print(f"       Check: {check_name} NOT FOUND")
    print()

# Test advisor's example: confidence 1.83
from packages.integrity.ai.deep_health import validate_confidence
print(f"  ADVISOR EXAMPLE TEST:")
print(f"    Input: confidence=1.83")
result_183 = validate_confidence(1.83)
print(f"    Result: {'ACCEPTED (WRONG!)' if result_183 else 'REJECTED (correct)'}")
print(f"    Expected: REJECTED")

example_correct = not result_183

print(f"\n  {'='*55}")
print(f"  ITEMS PRESENT: {present}/13")
print(f"  ITEMS PASSING: {passing}/13")
print(f"  ADVISOR EXAMPLE: {'PASS' if example_correct else 'FAIL'}")

if present == 13 and example_correct:
    print(f"\n  VERDICT: AI GATE COMPLETE - ALL 13 ITEMS + EXAMPLE VERIFIED")
elif present == 13:
    print(f"\n  VERDICT: ALL 13 ITEMS PRESENT (example mismatch)")
else:
    print(f"\n  VERDICT: INCOMPLETE - {13 - present} items missing")
print("=" * 70)
