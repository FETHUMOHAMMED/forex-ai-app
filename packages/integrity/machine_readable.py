"""Machine-Readable Result - Single JSON output for all components."""
import json
from datetime import datetime, timezone
from typing import Dict, List

def generate_machine_readable_result(
    scanner_results: List[dict],
    decision: str,
    trading_allowed: bool,
    critical_errors: List[dict],
) -> dict:
    """
    Generate THE single machine-readable result.
    Every component consumes this exact format.
    """
    domains = {}
    for result in scanner_results:
        domain = result.get("domain", "unknown")
        passed = result.get("passed", False)
        severity = result.get("severity", "WARNING")
        
        # Domain state: PASS/FAIL/DEGRADED
        if passed:
            domains[domain] = "PASS"
        elif severity == "CRITICAL":
            domains[domain] = "FAIL"
        else:
            domains[domain] = "DEGRADED"
    
    return {
        "system": "FOREX-AI-APP",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": decision,
        "trading_allowed": trading_allowed,
        "domains": domains,
        "critical_errors": critical_errors,
    }


def run_full_scanner() -> dict:
    """Run complete scanner and produce machine-readable result"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    
    # Import all domain checks
    import packages.integrity.api.health
    import packages.integrity.api.deep_health
    import packages.integrity.database.health
    import packages.integrity.database.deep_health
    import packages.integrity.mt5.connection
    import packages.integrity.mt5.deep_health
    import packages.integrity.mt5.remaining_checks
    import packages.integrity.ai.models
    import packages.integrity.ai.deep_health
    import packages.integrity.risk.budget
    import packages.integrity.risk.deep_health
    import packages.integrity.frontend.dashboard
    import packages.integrity.frontend.deep_health
    import packages.integrity.observability.deep_health
    
    from packages.integrity.registry import registry
    from packages.integrity.decision import make_decision, SystemDecision
    from packages.integrity.error_registry import ERROR_REGISTRY, Severity
    
    # Run all checks
    scanner_results = []
    for fn in registry.get_all():
        result = fn()
        scanner_results.append({
            "domain": result.domain,
            "check": result.check,
            "passed": result.passed,
            "severity": result.severity.value,
            "detail": result.detail,
        })
    
    # Make decision
    from packages.integrity.models import CheckResult
    from packages.integrity.severity import Severity as Sev
    
    check_objects = []
    for r in scanner_results:
        check_objects.append(CheckResult(
            domain=r["domain"], check=r["check"], passed=r["passed"],
            severity=Sev(r["severity"]), detail=r["detail"]
        ))
    
    decision = make_decision(check_objects)
    trading_allowed = decision != SystemDecision.HALT
    
    # Collect critical errors
    critical_errors = []
    for r in scanner_results:
        if not r["passed"] and r["severity"] == "CRITICAL":
            error_code = f"{r['domain'].upper()}_{r['check'].upper()}"
            critical_errors.append({
                "code": error_code,
                "severity": "CRITICAL",
                "detail": r["detail"],
            })
    
    return generate_machine_readable_result(
        scanner_results, decision.value, trading_allowed, critical_errors
    )


if __name__ == "__main__":
    result = run_full_scanner()
    
    # Output as JSON (machine-readable)
    print(json.dumps(result, indent=2))
    
    # Also save to file
    output_path = "ai-service/scanner_result.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n\nSaved to: {output_path}")
