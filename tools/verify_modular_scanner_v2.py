"""Verify Modular Scanner v2 - Fixed order: import domains first"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import domain checks FIRST (they register themselves)
import packages.integrity.api.health
import packages.integrity.database.health
import packages.integrity.mt5.connection
import packages.integrity.ai.models
import packages.integrity.risk.budget
import packages.integrity.frontend.dashboard

# Now check registry
from packages.integrity.registry import registry
check_count = len(registry.get_all())

print("=" * 60)
print("  MODULAR SCANNER VERIFICATION v2")
print("=" * 60)
print(f"\n  Registered checks: {check_count}")
print(f"  Expected: >= 6")
print(f"  Status: {'PASS' if check_count >= 6 else 'FAIL'}")
print(f"\n  Registered domains:")
for fn in registry.get_all():
    result = fn()
    print(f"    - {result.domain}/{result.check} [{result.severity.value}]")
print("=" * 60)
