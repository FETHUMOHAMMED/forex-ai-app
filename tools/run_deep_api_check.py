import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.api.deep_health

from packages.integrity.registry import registry

print("=" * 65)
print("  API INTEGRITY - DEEP CHECK (10 items)")
print("=" * 65)

for check_fn in registry.get_all():
    result = check_fn()
    if result.domain == 'api':
        icon = "PASS" if result.passed else "FAIL"
        print(f"  [{icon}] {result.check}")
        print(f"       {result.detail}")

passed = sum(1 for fn in registry.get_all() if fn().passed and fn().domain == 'api')
total = sum(1 for fn in registry.get_all() if fn().domain == 'api')
print(f"\n  API = {'HEALTHY' if passed == total else f'{passed}/{total} HEALTHY'}")
print("=" * 65)
