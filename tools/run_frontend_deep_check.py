import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.frontend.deep_health
from packages.integrity.registry import registry

print("=" * 65)
print("  FRONTEND GATE - DEEP CHECK (9 items)")
print("=" * 65)

fe_results = []
for fn in registry.get_all():
    result = fn()
    if result.domain == 'frontend':
        fe_results.append(result)
        icon = "PASS" if result.passed else "FAIL"
        print(f"  [{icon}] {result.check} [{result.severity.value}]")
        print(f"       {result.detail}")

passed = sum(1 for r in fe_results if r.passed)
total = len(fe_results)
print(f"\n  FRONTEND = {passed}/{total} PASSING")
print(f"  NOTE: Frontend failures are NON-CRITICAL")
print(f"  Trading may continue if frontend is down")
print("=" * 65)
