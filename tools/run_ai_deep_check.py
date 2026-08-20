import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.ai.deep_health
from packages.integrity.registry import registry

print("=" * 65)
print("  AI/ML GATE - DEEP CHECK (13 items)")
print("=" * 65)

ai_results = []
for fn in registry.get_all():
    result = fn()
    if result.domain == 'ai':
        ai_results.append(result)
        icon = "PASS" if result.passed else "FAIL"
        print(f"  [{icon}] {result.check} [{result.severity.value}]")
        print(f"       {result.detail}")

passed = sum(1 for r in ai_results if r.passed)
total = len(ai_results)
print(f"\n  AI = {passed}/{total} PASSING")

# Test advisor's example: confidence 1.83 should fail
from packages.integrity.ai.deep_health import validate_confidence
print(f"\n  ADVISOR EXAMPLE: confidence=1.83")
result = validate_confidence(1.83)
print(f"  Result: {'PASS' if result else 'FAIL (correctly rejected)'}")

print("=" * 65)
