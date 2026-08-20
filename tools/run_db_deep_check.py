import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.database.deep_health
from packages.integrity.registry import registry

print("=" * 65)
print("  DATABASE INTEGRITY - DEEP CHECK")
print("=" * 65)

db_results = []
for fn in registry.get_all():
    result = fn()
    if result.domain == 'database':
        db_results.append(result)
        icon = "PASS" if result.passed else "FAIL"
        print(f"  [{icon}] {result.check} [{result.severity.value}]")
        print(f"       {result.detail}")

passed = sum(1 for r in db_results if r.passed)
total = len(db_results)
print(f"\n  DATABASE = {'HEALTHY' if passed == total else str(passed) + '/' + str(total) + ' HEALTHY'}")
print("=" * 65)
