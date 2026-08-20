import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.mt5.deep_health
import packages.integrity.mt5.remaining_checks
from packages.integrity.registry import registry

print("=" * 65)
print("  MT5 FULL CHECK - 25 ITEMS")
print("=" * 65)

mt5_results = []
for fn in registry.get_all():
    result = fn()
    if result.domain == 'mt5':
        mt5_results.append(result)

# Sort by check name for stable display
mt5_results.sort(key=lambda r: r.check)

for i, result in enumerate(mt5_results, 1):
    icon = "PASS" if result.passed else "FAIL"
    print(f"  [{icon}] MT5-{i:03d} {result.check}")
    print(f"       {result.detail}")

passed = sum(1 for r in mt5_results if r.passed)
total = len(mt5_results)
print(f"\n  MT5 = {passed}/{total} PASSING")
if passed == total:
    print("  STATUS: ALL 25 ITEMS PASSING")
print("=" * 65)
