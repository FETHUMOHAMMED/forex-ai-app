"""Verify ALL 10 API Gate items per advisor specification"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

print("=" * 70)
print("  API GATE - 10 ITEM VERIFICATION")
print("=" * 70)

# Import all checks
import packages.integrity.api.deep_health
from packages.integrity.registry import registry

# The 10 advisor-required items
required_items = [
    ("API-001", "Process alive", "process_alive"),
    ("API-002", "HTTP responding", "http"),
    ("API-003", "Health endpoint", "health_endpoint"),
    ("API-004", "Database connectivity", "database_dependency"),
    ("API-005", "MT5 service connectivity", "mt5_dependency"),
    ("API-006", "Authentication working", "authentication"),
    ("API-007", "Expected API version", "version"),
    ("API-008", "Response latency", "latency"),
    ("API-009", "Required endpoints available", "endpoints"),
    ("API-010", "WebSocket connectivity", "websocket"),
]

# Run all API checks
api_results = {}
for fn in registry.get_all():
    result = fn()
    if result.domain == 'api':
        api_results[result.check] = result

print("\n  ADVISOR-REQUIRED ITEMS:")
print("  " + "-" * 55)

all_present = True
all_passing = True
for item_id, description, check_name in required_items:
    if check_name in api_results:
        result = api_results[check_name]
        icon = "PASS" if result.passed else "FAIL"
        print(f"  [{icon}] {item_id}: {description}")
        print(f"       Check: {check_name}")
        print(f"       Detail: {result.detail}")
        print(f"       Severity: {result.severity.value}")
        if not result.passed:
            all_passing = False
    else:
        icon = "MISSING"
        all_present = False
        print(f"  [{icon}] {item_id}: {description}")
        print(f"       Check: {check_name} NOT FOUND in registry")
    print()

print("  " + "=" * 55)
print(f"  ITEMS PRESENT: {sum(1 for _, _, c in required_items if c in api_results)}/10")
print(f"  ITEMS PASSING: {sum(1 for _, _, c in required_items if c in api_results and api_results[c].passed)}/10")

if all_present and all_passing:
    print(f"\n  VERDICT: ALL 10 ADVISOR ITEMS IMPLEMENTED AND PASSING")
elif all_present:
    print(f"\n  VERDICT: ALL 10 ITEMS PRESENT (some failing)")
else:
    print(f"\n  VERDICT: MISSING ITEMS - incomplete implementation")
print("=" * 70)
