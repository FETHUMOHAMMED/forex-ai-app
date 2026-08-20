import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.risk.deep_health
from packages.integrity.registry import registry

print("=" * 65)
print("  RISK GATE - DEEP CHECK (10 items)")
print("=" * 65)

risk_results = []
for fn in registry.get_all():
    result = fn()
    if result.domain == 'risk':
        risk_results.append(result)
        icon = "PASS" if result.passed else "FAIL"
        print(f"  [{icon}] {result.check} [{result.severity.value}]")
        print(f"       {result.detail}")

passed = sum(1 for r in risk_results if r.passed)
total = len(risk_results)
print(f"\n  RISK = {passed}/{total} PASSING")
if passed == total:
    print("  STATUS: ALL 10 ITEMS PASSING")
else:
    print(f"  STATUS: {total - passed} FAILURES - HALT")
print("=" * 65)
