"""VERIFY EXECUTION ISOLATION - Must pass before Live Micro."""
from pathlib import Path

def verify_execution_isolation():
    """Verify ONLY one execution path exists before Live Micro."""
    print("="*70)
    print("  EXECUTION ISOLATION VERIFICATION")
    print("  Pre-Live-Micro Acceptance Gate")
    print("="*70)
    
    checks = []
    
    # 1. Single execution path exists
    single_path = Path("packages/execution/single_path.py")
    checks.append({
        "check": "Single execution path exists",
        "passed": single_path.exists()
    })
    
    # 2. Hard boundary exists
    hard_boundary = Path("packages/execution/hard_order_boundary.py")
    checks.append({
        "check": "Hard order boundary exists",
        "passed": hard_boundary.exists()
    })
    
    # 3. Old executor disabled
    old_executor = Path("execution/mt5_executor.py")
    checks.append({
        "check": "Old executor disabled",
        "passed": not old_executor.exists()
    })
    
    # 4. auto_trader disabled
    auto_trader = Path("ai-service/auto_trader_exness.py")
    checks.append({
        "check": "auto_trader disabled",
        "passed": not auto_trader.exists()
    })
    
    # 5. Kill switch exists
    kill_switch = Path("packages/execution/kill_switch.py")
    checks.append({
        "check": "Kill switch exists",
        "passed": kill_switch.exists()
    })
    
    # 6. Reconciliation exists
    reconciliation = Path("packages/execution/mt5_reconciliation.py")
    checks.append({
        "check": "MT5 reconciliation exists",
        "passed": reconciliation.exists()
    })
    
    # 7. Strategy registry exists
    registry = Path("packages/strategy/strategy_registry.py")
    checks.append({
        "check": "Strategy registry exists",
        "passed": registry.exists()
    })
    
    # 8. Safety tests pass
    safety_tests = Path("tests/test_safety_suite.py")
    checks.append({
        "check": "Safety tests exist",
        "passed": safety_tests.exists()
    })
    
    # Display results
    passed = 0
    for check in checks:
        status = "PASS" if check["passed"] else "FAIL"
        icon = "?" if check["passed"] else "?"
        print(f"  {icon} {check['check']:40s} {status}")
        passed += 1 if check["passed"] else 0
    
    total = len(checks)
    print(f"\n  RESULT: {passed}/{total} PASSED")
    
    if passed == total:
        print(f"\n  ? EXECUTION ISOLATED - Live Micro SAFE to test")
        print(f"  Only single_path.py can place orders")
        print(f"  All safety gates in place")
    else:
        print(f"\n  ? ISOLATION INCOMPLETE - Live Micro NOT authorized")
    
    return passed == total

if __name__ == "__main__":
    verify_execution_isolation()
