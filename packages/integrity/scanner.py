"""Unified Scanner - Runs ALL registered checks and makes decision"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from packages.integrity.registry import registry
from packages.integrity.decision import make_decision, SystemDecision
from packages.integrity.models import CheckResult

# Import all domain checks
import packages.integrity.api.health
import packages.integrity.database.health
import packages.integrity.mt5.connection
import packages.integrity.ai.models
import packages.integrity.risk.budget
import packages.integrity.frontend.dashboard

def run_scanner() -> dict:
    results = []
    for check_fn in registry.get_all():
        result = check_fn()
        results.append(result)
    
    decision = make_decision(results)
    return {
        "decision": decision.value,
        "results": [
            {"domain": r.domain, "check": r.check, "passed": r.passed,
             "severity": r.severity.value, "detail": r.detail}
            for r in results
        ],
    }

def print_scanner_report():
    data = run_scanner()
    
    icons = {"READY": "[READY]", "DEGRADED": "[DEGRADED]", "HALT": "[HALT]"}
    print("=" * 65)
    print("  SYSTEM INTEGRITY SCANNER (Modular)")
    print("=" * 65)
    
    for r in data["results"]:
        icon = "PASS" if r["passed"] else "FAIL"
        print(f"  [{icon}] {r['domain']}/{r['check']} [{r['severity']}]")
        print(f"       {r['detail']}")
    
    decision = data["decision"]
    print(f"\n  DECISION: {icons.get(decision, '[UNKNOWN]')} {decision}")
    trading = "BLOCKED" if decision == "HALT" else "ALLOWED"
    print(f"  TRADING: {trading}")
    print("=" * 65)
    return data

if __name__ == "__main__":
    print_scanner_report()
