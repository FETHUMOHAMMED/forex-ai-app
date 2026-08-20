"""Verify Modular Scanner - All advisor requirements"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

print("=" * 70)
print("  MODULAR SCANNER VERIFICATION")
print("=" * 70)

checks = []
def verify(name, passed, detail=""):
    icon = "[PASS]" if passed else "[FAIL]"
    checks.append(passed)
    print(f"  {icon} {name}")
    if detail:
        print(f"       {detail}")

# 1. Package structure
print("\n--- A. PACKAGE STRUCTURE ---")
required_dirs = [
    "packages/integrity",
    "packages/integrity/api",
    "packages/integrity/database",
    "packages/integrity/mt5",
    "packages/integrity/ai",
    "packages/integrity/execution",
    "packages/integrity/risk",
    "packages/integrity/frontend",
    "packages/integrity/tests",
]
all_dirs = all(Path(d).exists() for d in required_dirs)
verify("All 9 domain directories exist", all_dirs)

# 2. Core modules
print("\n--- B. CORE MODULES ---")
core_files = [
    "packages/integrity/scanner.py",
    "packages/integrity/models.py",
    "packages/integrity/severity.py",
    "packages/integrity/decision.py",
    "packages/integrity/registry.py",
]
all_core = all(Path(f).exists() for f in core_files)
verify(f"All 5 core modules ({len(core_files)})", all_core)

# 3. Severity levels
print("\n--- C. SEVERITY LEVELS ---")
from packages.integrity.severity import Severity
verify("CRITICAL level", hasattr(Severity, 'CRITICAL'))
verify("WARNING level", hasattr(Severity, 'WARNING'))
verify("INFO level", hasattr(Severity, 'INFO'))

# 4. Three states
print("\n--- D. DECISION STATES ---")
from packages.integrity.decision import SystemDecision
verify("READY state", hasattr(SystemDecision, 'READY'))
verify("DEGRADED state", hasattr(SystemDecision, 'DEGRADED'))
verify("HALT state", hasattr(SystemDecision, 'HALT'))

# 5. Registry pattern
print("\n--- E. REGISTRY PATTERN ---")
from packages.integrity.registry import registry
check_count = len(registry.get_all())
verify(f"Registry has registered checks ({check_count})", check_count >= 6)

# 6. Domain checks registered
print("\n--- F. DOMAIN CHECKS ---")
domains_found = set()
import packages.integrity.api.health
import packages.integrity.database.health
import packages.integrity.mt5.connection
import packages.integrity.ai.models
import packages.integrity.risk.budget
import packages.integrity.frontend.dashboard

for check_fn in registry.get_all():
    result = check_fn()
    domains_found.add(result.domain)

verify(f"Distinct domains: {domains_found}", len(domains_found) >= 6, 
       f"Found: {domains_found}")

# 7. Run scanner
print("\n--- G. RUN SCANNER ---")
from packages.integrity.scanner import run_scanner, print_scanner_report
data = run_scanner()
verify("Scanner runs", "decision" in data)
verify("Decision is valid", data["decision"] in ["READY", "DEGRADED", "HALT"])

# 8. Show actual results
print(f"\n  SCANNER RESULTS ({len(data['results'])} checks):")
for r in data["results"]:
    icon = "PASS" if r["passed"] else "FAIL"
    print(f"    [{icon}] {r['domain']}/{r['check']} [{r['severity']}]")

print(f"\n  DECISION: {data['decision']}")
trading = "BLOCKED" if data["decision"] == "HALT" else "ALLOWED"
print(f"  TRADING: {trading}")

print(f"\n{'='*70}")
total = sum(checks)
print(f"  RESULT: {total}/{len(checks)} CHECKS PASSED")
if total == len(checks):
    print(f"  STATUS: MODULAR SCANNER FULLY IMPLEMENTED")
print(f"{'='*70}")
