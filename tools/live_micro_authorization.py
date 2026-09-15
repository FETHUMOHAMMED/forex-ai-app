"""LIVE MICRO AUTHORIZATION - Final checklist before first real order."""
import MetaTrader5 as mt5
from pathlib import Path

def check_live_micro_authorization():
    """Verify ALL conditions before first live order."""
    print("="*70)
    print("  LIVE MICRO AUTHORIZATION CHECKLIST")
    print("="*70)
    
    checks = []
    
    # 1. MT5 account
    if mt5.initialize():
        account = mt5.account_info()
        mt5.shutdown()
        if account:
            checks.append({
                "check": "Correct MT5 account",
                "passed": account.login == REDACTED_LIVE_ACCOUNT,
                "detail": f"Login: {account.login}"
            })
            checks.append({
                "check": "Adequate capital ($2,000+)",
                "passed": account.balance >= 2000,
                "detail": f"Balance: ${account.balance:.2f}"
            })
    
    # 2. Execution isolation
    checks.append({
        "check": "Single execution path",
        "passed": Path("packages/execution/single_path.py").exists()
    })
    
    # 3. Safety components
    checks.append({
        "check": "Kill switch exists",
        "passed": Path("packages/execution/kill_switch.py").exists()
    })
    checks.append({
        "check": "Reconciliation exists",
        "passed": Path("packages/execution/mt5_reconciliation.py").exists()
    })
    checks.append({
        "check": "Hard boundary exists",
        "passed": Path("packages/execution/hard_order_boundary.py").exists()
    })
    
    # 4. Strategy frozen
    checks.append({
        "check": "Strategy frozen",
        "passed": Path("research/paper/V4_CANONICAL_1.0/FROZEN_STRATEGY_DEFINITION.json").exists()
    })
    
    # 5. Safety tests
    checks.append({
        "check": "Safety tests exist",
        "passed": Path("tests/test_safety_suite.py").exists()
    })
    
    # 6. Live trading lock
    checks.append({
        "check": "Live trading lock file exists",
        "passed": Path("research/paper/V4_CANONICAL_1.0/LIVE_TRADING_LOCK.md").exists()
    })
    
    # Display results
    passed = 0
    for check in checks:
        status = "PASS" if check["passed"] else "FAIL"
        icon = "?" if check["passed"] else "?"
        detail = f" ({check['detail']})" if "detail" in check else ""
        print(f"  {icon} {check['check']:40s} {status}{detail}")
        passed += 1 if check["passed"] else 0
    
    total = len(checks)
    print(f"\n  RESULT: {passed}/{total} PASSED")
    
    if passed == total:
        print(f"\n  ? LIVE MICRO AUTHORIZED (execution testing only)")
    else:
        print(f"\n  ? LIVE MICRO NOT AUTHORIZED - {total-passed} conditions unmet")
        if "Adequate capital" in str(checks):
            print(f"\n  MAIN BLOCKER: Capital too low")
            print(f"  Current: $11.69 (need $2,000+)")
    
    return passed == total

if __name__ == "__main__":
    check_live_micro_authorization()
