import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.observability.deep_health
from packages.integrity.registry import registry

print("=" * 65)
print("  OBSERVABILITY GATE - DEEP CHECK")
print("=" * 65)

obs_results = []
for fn in registry.get_all():
    result = fn()
    if result.domain == 'observability':
        obs_results.append(result)
        icon = "PASS" if result.passed else "FAIL"
        print(f"  [{icon}] {result.check} [{result.severity.value}]")
        print(f"       {result.detail}")

passed = sum(1 for r in obs_results if r.passed)
total = len(obs_results)
print(f"\n  OBSERVABILITY = {passed}/{total} PASSING")
print("=" * 65)
