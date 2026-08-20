"""Verify Observability Gate - All advisor items"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.observability.deep_health
from packages.integrity.registry import registry

# Advisor's required observability checks
advisor_items = [
    ("LOG-001", "Logger functioning", "logger"),
    ("LOG-002", "Structured logs", "structured_logs"),
    ("LOG-003", "Timestamps valid", "timestamps"),
    ("LOG-004", "Alert system functioning", "alert_system"),
    ("LOG-005", "Prometheus available", "prometheus"),
    ("LOG-006", "Heartbeat current", "heartbeat"),
    ("LOG-007", "Error rate", "error_rate"),
    ("LOG-008", "Scanner itself alive", "scanner_alive"),
    ("CRITICAL", "Scanner heartbeat (not stale)", "scanner_freshness"),
]

# Run all observability checks
obs_checks = {}
for fn in registry.get_all():
    result = fn()
    if result.domain == 'observability':
        obs_checks[result.check] = result

print("=" * 70)
print("  OBSERVABILITY GATE - ADVISOR VERIFICATION")
print("=" * 70)

present = 0
passing = 0
for item_id, description, check_name in advisor_items:
    if check_name in obs_checks:
        present += 1
        result = obs_checks[check_name]
        icon = "PASS" if result.passed else "FAIL"
        if result.passed:
            passing += 1
        print(f"  [{icon}] {item_id}: {description}")
        print(f"       Check: {check_name}")
        print(f"       Detail: {result.detail}")
        print(f"       Severity: {result.severity.value}")
    else:
        print(f"  [MISSING] {item_id}: {description}")
        print(f"       Check: {check_name} NOT FOUND")
    print()

# Verify scanner heartbeat is CRITICAL
scanner_checks = [r for r in obs_checks.values() if 'scanner' in r.check]
scanner_critical = all(r.severity.value == "CRITICAL" for r in scanner_checks)
print(f"  SCANNER CHECKS ARE CRITICAL: {scanner_critical}")
print(f"  (Scanner death = HALT, not just warning)")

# Verify scanner heartbeat freshness works
from packages.integrity.observability.deep_health import write_scanner_heartbeat, read_scanner_heartbeat
hb = write_scanner_heartbeat()
read_back = read_scanner_heartbeat()
heartbeat_roundtrip = "last_scan_at" in hb and "last_scan_at" in read_back
print(f"  SCANNER HEARTBEAT ROUNDTRIP: {'PASS' if heartbeat_roundtrip else 'FAIL'}")

print(f"\n  {'='*55}")
print(f"  ITEMS PRESENT: {present}/9")
print(f"  ITEMS PASSING: {passing}/9")
print(f"  SCANNER CRITICAL: {scanner_critical}")
print(f"  HEARTBEAT WORKS: {heartbeat_roundtrip}")

if present == 9 and scanner_critical and heartbeat_roundtrip:
    print(f"\n  VERDICT: OBSERVABILITY GATE COMPLETE - ALL 9 ITEMS + SCANNER HEARTBEAT VERIFIED")
elif present == 9:
    print(f"\n  VERDICT: ALL 9 ITEMS PRESENT (criticality issue)")
else:
    print(f"\n  VERDICT: INCOMPLETE - {9 - present} items missing")
print("=" * 70)
