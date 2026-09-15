"""SYNTHETIC SIGNAL TEST - Valid order + Invalid order."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.execution.hard_order_boundary import OrderRequest, OrderDirection
from packages.execution.single_path import SingleExecutionPath

def test_valid_order():
    """Test that a VALID order (SL >= 10 pips) passes."""
    print(f"\n  TEST A: VALID ORDER (SL=10 pips, TP=20 pips)")
    valid_order = OrderRequest(
        symbol="USDJPYm",
        direction=OrderDirection.BUY,
        volume=0.01,
        entry=154.250,
        sl=154.140,  # 11 pips below (safely above 10-pip minimum)
        tp=154.470,  # 22 pips above (2R)
        risk_percent=0.25,
        account="REDACTED_LIVE_ACCOUNT",
        strategy_version="V4_CANONICAL_1.0"
    )
    execution = SingleExecutionPath()
    result = execution.execute_order(valid_order, mode="PAPER")
    print(f"    Status: {result['status']}")
    print(f"    MT5 called: {result['mt5_called']}")
    assert result['status'] == "PAPER_EXECUTED", f"Expected PAPER_EXECUTED, got {result['status']}"
    return True

def test_invalid_order():
    """Test that an INVALID order (SL < 10 pips) is REJECTED."""
    print(f"\n  TEST B: INVALID ORDER (SL=6 pips, below minimum)")
    invalid_order = OrderRequest(
        symbol="USDJPYm",
        direction=OrderDirection.BUY,
        volume=0.01,
        entry=154.250,
        sl=154.190,  # Only 6 pips (below 10-pip minimum)
        tp=154.370,
        risk_percent=0.25,
        account="REDACTED_LIVE_ACCOUNT",
        strategy_version="V4_CANONICAL_1.0"
    )
    execution = SingleExecutionPath()
    result = execution.execute_order(invalid_order, mode="PAPER")
    print(f"    Status: {result['status']}")
    print(f"    MT5 called: {result['mt5_called']}")
    assert result['status'] == "REJECTED", f"Expected REJECTED, got {result['status']}"
    assert result['mt5_called'] == False
    return True

if __name__ == "__main__":
    print("="*70)
    print("  SYNTHETIC SIGNAL TEST (BOTH CASES)")
    print("="*70)
    
    valid_passed = test_valid_order()
    invalid_passed = test_invalid_order()
    
    print(f"\n{'='*70}")
    print(f"  VALID ORDER: {'PASS' if valid_passed else 'FAIL'}")
    print(f"  INVALID ORDER REJECTED: {'PASS' if invalid_passed else 'FAIL'}")
    print("="*70)
    
    if valid_passed and invalid_passed:
        print("\n  ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n  TESTS FAILED")
        sys.exit(1)

