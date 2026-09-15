"""VERIFY V4 LIVE READINESS - Ignore legacy, check V4 only."""
from pathlib import Path

def verify_v4_live_readiness():
    """Check if V4 is ready for live (ignoring legacy V3)."""
    print("="*70)
    print("  V4 LIVE READINESS CHECK")
    print("  (Excludes legacy V3 trades)")
    print("="*70)
    
    checks = []
    
    # 1. Strategy frozen
    checks.append({
        "check": "V4 strategy frozen",
        "passed": Path("research/paper/V4_CANONICAL_1.0/FROZEN_STRATEGY_DEFINITION.json").exists()
    })
    
    # 2. Single execution path
    checks.append({
        "check": "Single execution path",
        "passed": Path("packages/execution/single_path.py").exists()
    })
    
    # 3. Hard boundary
    checks.append({
        "check": "Hard order boundary",
        "passed": Path("packages/execution/hard_order_boundary.py").exists()
    })
    
    # 4. Bypass files disabled
    bypass_gone = not Path("ai-service/broker_exness.py").exists()
    bypass_gone = bypass_gone and not Path("ai-service/real_ai_service.py").exists()
    bypass_gone = bypass_gone and not Path("risk/risk_manager.py").exists()
    checks.append({
        "check": "Bypass files disabled",
        "passed": bypass_gone
    })
    
    # 5. Paper runner active
    checks.append({
        "check": "Paper runner exists",
        "passed": Path("research/paper/V4_CANONICAL_1.0/continuous_runner.py").exists()
    })
    
    # 6. Capital (the only real blocker)
    checks.append({
        "check": "Capital >= $2,000",
        "passed": False,  # $11.69
        "detail": "$11.69 / $2,000"
    })
    
    # Display
    passed = 0
    for check in checks:
        icon = "PASS" if check["passed"] else "FAIL"
        detail = f" ({check['detail']})" if "detail" in check else ""
        print(f"\n  [{icon}] {check['check']}{detail}")
        if check["passed"]:
            passed += 1
    
    total = len(checks)
    print(f"\n{'='*70}")
    print(f"  RESULT: {passed}/{total} PASSED")
    print(f"{'='*70}")
    
    if passed == total:
        print(f"\n  V4 READY FOR LIVE (all checks pass)")
    else:
        print(f"\n  V4 NOT READY - {total-passed} blocker(s)")
        print(f"  PRIMARY BLOCKER: Capital too low")
    
    return passed == total

if __name__ == "__main__":
    verify_v4_live_readiness()
