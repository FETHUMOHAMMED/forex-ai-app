"""Verify Error Registry matches advisor's exact specification"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.integrity.error_registry import ERROR_REGISTRY, ErrorCode, Severity, Action

print("=" * 75)
print("  ERROR REGISTRY - ADVISOR VERIFICATION")
print("=" * 75)

# Advisor's exact required entries
advisor_required = [
    ("MT5_DISCONNECTED", "CRITICAL", "HALT"),
    ("DB_UNAVAILABLE", "CRITICAL", "HALT"),
    ("RISK_UNAVAILABLE", "CRITICAL", "HALT"),
    ("SL_INVALID", "CRITICAL", "BLOCK_ORDER"),
    ("TP_INVALID", "CRITICAL", "BLOCK_ORDER"),
    ("STALE_SIGNAL", "HIGH", "BLOCK_ORDER"),
    ("ENTRY_DEVIATION", "HIGH", "BLOCK_ORDER"),
    ("FRONTEND_DOWN", "MEDIUM", "DEGRADED"),
    ("PROMETHEUS_DOWN", "LOW", "ALERT"),
    ("MODEL_LOAD_WARNING", "HIGH", "BLOCK_AI"),
]

print(f"\n  ADVISOR'S REQUIRED ENTRIES ({len(advisor_required)}):")
print(f"  {'-'*55}")

all_match = True
for code, expected_severity, expected_action in advisor_required:
    entry = ERROR_REGISTRY.get(code)
    if entry:
        sev_match = entry.severity.value == expected_severity
        act_match = entry.action.value == expected_action
        match = sev_match and act_match
        if not match:
            all_match = False
        
        icon = "MATCH" if match else "MISMATCH"
        print(f"  [{icon}] {code}")
        print(f"       Expected: {expected_severity} -> {expected_action}")
        print(f"       Actual:   {entry.severity.value} -> {entry.action.value}")
    else:
        all_match = False
        print(f"  [MISSING] {code}")
        print(f"       Expected: {expected_severity} -> {expected_action}")
    print()

print(f"  {'='*55}")
print(f"  ADVISOR ENTRIES MATCHING: {sum(1 for c, s, a in advisor_required if c in ERROR_REGISTRY and ERROR_REGISTRY[c].severity.value == s and ERROR_REGISTRY[c].action.value == a)}/{len(advisor_required)}")

# Check additional entries exist beyond advisor's minimum
extra_codes = set(ERROR_REGISTRY.keys()) - {c for c, _, _ in advisor_required}
print(f"  ADDITIONAL CODES: {len(extra_codes)} extra beyond advisor's minimum")
for code in sorted(extra_codes):
    entry = ERROR_REGISTRY[code]
    print(f"    - {code}: {entry.severity.value} -> {entry.action.value}")

# Verify not hard-coded in scanner.py
scanner_content = Path("packages/integrity/scanner.py").read_text()
registry_imported = "error_registry" in scanner_content or "ERROR_REGISTRY" in scanner_content
print(f"\n  REGISTRY IS SEPARATE MODULE: {'PASS' if not registry_imported else 'WARNING - may be imported'}")

print(f"\n  VERDICT:")
if all_match and len(extra_codes) > 0:
    print(f"  ERROR REGISTRY COMPLETE - ALL 10 ADVISOR ENTRIES MATCH + {len(extra_codes)} EXTRA")
elif all_match:
    print(f"  ERROR REGISTRY COMPLETE - ALL 10 ADVISOR ENTRIES MATCH")
else:
    print(f"  ISSUES FOUND - some entries mismatch")
print("=" * 75)
