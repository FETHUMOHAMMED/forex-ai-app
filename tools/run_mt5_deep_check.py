import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.mt5.deep_health
from packages.integrity.registry import registry

print("=" * 65)
print("  MT5 INTEGRITY - DEEP CHECK")
print("=" * 65)

mt5_results = []
for fn in registry.get_all():
    result = fn()
    if result.domain == 'mt5':
        mt5_results.append(result)
        icon = "PASS" if result.passed else "FAIL"
        print(f"  [{icon}] {result.check} [{result.severity.value}]")
        print(f"       {result.detail}")

passed = sum(1 for r in mt5_results if r.passed)
total = len(mt5_results)
print(f"\n  MT5 = {'HEALTHY' if passed == total else str(passed) + '/' + str(total) + ' HEALTHY'}")
print("=" * 65)
