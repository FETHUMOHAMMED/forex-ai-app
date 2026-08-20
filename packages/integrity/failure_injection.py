"""Runtime Failure Injection Gate - Deliberately corrupt every boundary."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone, timedelta
from enum import Enum

class Environment(str, Enum):
    SIMULATED = "SIMULATED"
    PAPER = "PAPER"
    LIVE_VALIDATION = "LIVE_VALIDATION"
    LIVE_PRODUCTION = "LIVE_PRODUCTION"

class FailureTest:
    """One failure injection test."""
    def __init__(self, name: str, expected_action: str):
        self.name = name
        self.expected_action = expected_action
        self.result = None
        self.passed = False
        self.unsafe = False  # True if system allowed something it shouldn't

BASE_IDENTITY = {
    "signal_id": "SIG_VALID",
    "account_id": REDACTED_LIVE_ACCOUNT,
    "MT5_login": REDACTED_LIVE_ACCOUNT,
    "account_name": "Live_Micro",
    "pair": "EURUSD",
    "direction": "SELL",
    "strategy_version": "V3_REGIME",
    "model_version": "v1.0",
    "entry": 1.15542,
    "SL": 1.15718,
    "TP": 1.15261,
    "volume": 0.01,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "position_ticket": 592780483,
    "deal_ticket": 591026126,
}

def verify_identity(identity: dict, context: str = "test") -> tuple:
    """
    Verify identity integrity. Returns (is_valid, action, reason).
    """
    # Check account consistency
    if identity.get("account_id") != identity.get("MT5_login"):
        return False, "BLOCK", "account_id != MT5_login"
    
    # account_name must MATCH account_id
    account_mapping = {
        REDACTED_LIVE_ACCOUNT: "Live_Micro",
        REDACTED_DEMO_ACCOUNT: "Demo2",
    }
    expected_name = account_mapping.get(identity.get("account_id"))
    if identity.get("account_name") != expected_name:
        return False, "BLOCK", f"account_name {identity.get('account_name')} != expected {expected_name} for account_id {identity.get('account_id')}"
    
    # Check signal ID
    if not identity.get("signal_id"):
        return False, "BLOCK", "Missing signal_id"
    
    # Check pair
    if identity.get("pair", "").endswith("m"):
        return False, "BLOCK", "Pair must be normalized (no 'm' suffix)"
    
    # Check direction
    if identity.get("direction") not in ("BUY", "SELL", "NO_TRADE"):
        return False, "BLOCK", f"Invalid direction: {identity.get('direction')}"
    
    # Check strategy
    if identity.get("strategy_version") != "V3_REGIME":
        return False, "BLOCK", f"Wrong strategy: {identity.get('strategy_version')}"
    
    # Check prices
    if identity.get("entry", 0) <= 0:
        return False, "BLOCK", "Invalid entry price"
    
    if identity.get("SL", 0) <= 0:
        return False, "BLOCK", "Invalid SL"
    
    if identity.get("TP", 0) <= 0:
        return False, "BLOCK", "Invalid TP"
    
    # Check SL/TP direction
    if identity.get("direction") == "SELL":
        if identity.get("SL", 0) <= identity.get("entry", 0):
            return False, "BLOCK", "SL below entry for SELL"
        if identity.get("TP", 0) >= identity.get("entry", 0):
            return False, "BLOCK", "TP above entry for SELL"
    elif identity.get("direction") == "BUY":
        if identity.get("SL", 0) >= identity.get("entry", 0):
            return False, "BLOCK", "SL above entry for BUY"
        if identity.get("TP", 0) <= identity.get("entry", 0):
            return False, "BLOCK", "TP below entry for BUY"
    
    # Check volume
    if identity.get("volume", 0) > 0.01:
        return False, "BLOCK", f"Volume {identity.get('volume')} exceeds 0.01 max"
    
    # Check tickets
    if not identity.get("position_ticket"):
        return False, "BLOCK", "Missing position_ticket"
    
    if not identity.get("deal_ticket"):
        return False, "BLOCK", "Missing deal_ticket"
    
    return True, "ALLOW", "All checks passed"


def run_failure_injection():
    """Run all failure injection tests."""
    tests = [
        ("Change signal_id", {**BASE_IDENTITY, "signal_id": ""}, "BLOCK"),
        ("Change account_id", {**BASE_IDENTITY, "account_id": REDACTED_DEMO_ACCOUNT}, "BLOCK"),
        ("Change MT5 login", {**BASE_IDENTITY, "MT5_login": REDACTED_DEMO_ACCOUNT}, "BLOCK"),
        ("Change account name", {**BASE_IDENTITY, "account_name": "Demo2"}, "BLOCK"),
        ("Change pair (with suffix)", {**BASE_IDENTITY, "pair": "EURUSDm"}, "BLOCK"),
        ("Change direction to invalid", {**BASE_IDENTITY, "direction": "Yes"}, "BLOCK"),
        ("Change strategy version", {**BASE_IDENTITY, "strategy_version": "V2"}, "BLOCK"),
        ("Change entry", {**BASE_IDENTITY, "entry": 1.16000}, "BLOCK"),
        ("Change SL (wrong side)", {**BASE_IDENTITY, "SL": 1.15000}, "BLOCK"),
        ("Change TP (wrong side)", {**BASE_IDENTITY, "TP": 1.16000}, "BLOCK"),
        ("Change volume (1.0)", {**BASE_IDENTITY, "volume": 1.0}, "BLOCK"),
        ("Missing position_ticket", {**BASE_IDENTITY, "position_ticket": None}, "BLOCK"),
        ("Missing deal_ticket", {**BASE_IDENTITY, "deal_ticket": None}, "BLOCK"),
        ("Missing signal_id", {**BASE_IDENTITY, "signal_id": None}, "BLOCK"),
        ("Change account_id != MT5_login", {**BASE_IDENTITY, "account_id": REDACTED_LIVE_ACCOUNT, "MT5_login": REDACTED_DEMO_ACCOUNT}, "BLOCK"),
    ]
    
    results = []
    for name, corrupted_identity, expected_action in tests:
        is_valid, action, reason = verify_identity(corrupted_identity, name)
        passed = action == expected_action
        unsafe = is_valid and expected_action == "BLOCK"  # System allowed what it should block
        results.append({
            "test": name, "passed": passed, "unsafe": unsafe,
            "action": action, "expected": expected_action, "reason": reason,
        })
    
    return results


def print_failure_injection_report():
    """Print complete failure injection report."""
    print("=" * 75)
    print("  RUNTIME FAILURE-INJECTION GATE")
    print("=" * 75)
    
    print(f"\n  ENVIRONMENT: LIVE_VALIDATION")
    print(f"  TRADE: TRADE_001")
    print()
    
    results = run_failure_injection()
    
    passed = sum(1 for r in results if r["passed"] and not r["unsafe"])
    failed = sum(1 for r in results if not r["passed"])
    unsafe = sum(1 for r in results if r["unsafe"])
    
    print(f"  FAILURE INJECTION TESTS:")
    print(f"  {'-'*55}")
    for r in results:
        icon = "PASS" if r["passed"] and not r["unsafe"] else "UNSAFE" if r["unsafe"] else "FAIL"
        print(f"    [{icon}] {r['test']}")
        print(f"         Action: {r['action']} (expected {r['expected']})")
    
    print(f"\n  {'='*55}")
    print(f"  Tests: {len(results)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Unsafe passes: {unsafe}")
    
    print(f"\n  RESULT: {'PASS' if passed == len(results) and unsafe == 0 else 'FAIL'}")
    
    print(f"\n  STATISTICAL VALIDATION: NOT ESTABLISHED")
    print(f"  PROFITABILITY VALIDATION: NOT ESTABLISHED")
    print(f"  PRODUCTION AUTHORIZATION: DENIED")
    print("=" * 75)


if __name__ == "__main__":
    print_failure_injection_report()
