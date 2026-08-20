"""Preflight Scanner - Complete system check before live validation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
from datetime import datetime, timezone

def run_preflight() -> dict:
    """Run complete preflight check"""
    print("=" * 70)
    print("  FOREX-AI-APP SYSTEM PREFLIGHT")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)
    
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
    import packages.integrity.execution.gate
    
    from packages.integrity.registry import registry
    from packages.integrity.decision import make_decision, SystemDecision
    from packages.integrity.models import CheckResult
    from packages.integrity.severity import Severity
    
    # Run ALL checks
    results = []
    print()
    
    current_domain = None
    for fn in registry.get_all():
        result = fn()
        
        # Print domain header when domain changes
        if result.domain != current_domain:
            current_domain = result.domain
            print(f"\n  {result.domain.upper()}")
        
        icon = "PASS" if result.passed else "FAIL"
        print(f"    [{icon}] {result.check}")
        
        results.append(CheckResult(
            domain=result.domain, check=result.check,
            passed=result.passed, severity=result.severity,
            detail=result.detail
        ))
    
    # Make decision
    decision = make_decision(results)
    trading_allowed = decision != SystemDecision.HALT
    
    # Collect critical failures
    critical_failures = [r for r in results if not r.passed and r.severity == Severity.CRITICAL]
    
    print(f"\n{'='*70}")
    print(f"  SYSTEM: {decision.value}")
    print(f"  TRADING: {'ALLOWED' if trading_allowed else 'BLOCKED'}")
    
    if critical_failures:
        print(f"\n  CRITICAL FAILURES:")
        for r in critical_failures:
            print(f"    - {r.domain}/{r.check}: {r.detail}")
    
    print("=" * 70)
    
    return {
        "system": "FOREX-AI-APP",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": decision.value,
        "trading_allowed": trading_allowed,
        "total_checks": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "critical_failures": len(critical_failures),
    }

if __name__ == "__main__":
    run_preflight()
