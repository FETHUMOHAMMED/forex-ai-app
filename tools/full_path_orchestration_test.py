"""FULL-PATH ORCHESTRATION TEST - Valid + Invalid paths through runner."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.execution.hard_order_boundary import OrderRequest, OrderDirection
from packages.execution.single_path import SingleExecutionPath
from packages.execution.live_micro_runner import LiveMicroRunner

def test_valid_full_path():
    """Test VALID order goes through full orchestration."""
    print("="*70)
    print("  TEST A: VALID ORDER - FULL PATH")
    print("="*70)
    
    valid_order = OrderRequest(
        symbol="USDJPYm",
        direction=OrderDirection.BUY,
        volume=0.01,
        entry=154.250,
        sl=154.140,  # 11 pips (above 10-pip minimum)
        tp=154.470,  # 22 pips (2R)
        risk_percent=0.25,
        account="REDACTED_LIVE_ACCOUNT",
        strategy_version="V4_CANONICAL_1.0"
    )
    
    execution = SingleExecutionPath()
    result = execution.execute_order(valid_order, mode="PAPER")
    
    print(f"    OrderRequest: CREATED")
    print(f"    HardOrderBoundary: {'PASS' if result['status'] == 'PAPER_EXECUTED' else 'FAIL'}")
    print(f"    SingleExecutionPath: {result['status']}")
    print(f"    MT5 called: {result['mt5_called']}")
    
    assert result['status'] == "PAPER_EXECUTED"
    assert result['mt5_called'] == False
    print(f"\n  RESULT: PASS ?")
    return True

def test_invalid_full_path():
    """Test INVALID order is rejected through full orchestration."""
    print(f"\n{'='*70}")
    print("  TEST B: INVALID ORDER - REJECTION PATH")
    print("="*70)
    
    invalid_order = OrderRequest(
        symbol="USDJPYm",
        direction=OrderDirection.BUY,
        volume=0.01,
        entry=154.250,
        sl=154.190,  # 6 pips (BELOW 10-pip minimum)
        tp=154.370,
        risk_percent=0.25,
        account="REDACTED_LIVE_ACCOUNT",
        strategy_version="V4_CANONICAL_1.0"
    )
    
    execution = SingleExecutionPath()
    result = execution.execute_order(invalid_order, mode="PAPER")
    
    print(f"    OrderRequest: CREATED")
    print(f"    HardOrderBoundary: {'REJECTED' if result['status'] == 'REJECTED' else 'ERROR'}")
    print(f"    SingleExecutionPath: {result['status']}")
    print(f"    MT5 called: {result['mt5_called']}")
    
    assert result['status'] == "REJECTED"
    assert result['mt5_called'] == False
    print(f"\n  RESULT: PASS ? (correctly rejected)")
    return True

def test_no_signal_path():
    """Test NO_SIGNAL path (like the runner showed)."""
    print(f"\n{'='*70}")
    print("  TEST C: NO_SIGNAL PATH")
    print("="*70)
    
    runner = LiveMicroRunner(mode="PAPER")
    runner.initialize()
    result = runner.check_and_execute()
    runner.shutdown()
    
    print(f"    Result: {result['status']}")
    print(f"    Reason: {result.get('reason', 'N/A')}")
    print(f"    MT5 called: {result.get('mt5_called', False)}")
    
    assert result['mt5_called'] == False
    print(f"\n  RESULT: PASS ? (NO_SIGNAL handled correctly)")
    return True

if __name__ == "__main__":
    print("="*70)
    print("  FULL-PATH ORCHESTRATION TEST SUITE")
    print("="*70)
    
    results = []
    results.append(("Valid order full path", test_valid_full_path()))
    results.append(("Invalid order rejection", test_invalid_full_path()))
    results.append(("NO_SIGNAL handling", test_no_signal_path()))
    
    print(f"\n{'='*70}")
    print("  SUMMARY")
    print("="*70)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
    
    print(f"\n  RESULT: {passed}/{total} PASSED")
    
    if passed == total:
        print("\n  ALL FULL-PATH TESTS PASSED")
        sys.exit(0)
    else:
        print("\n  TESTS FAILED")
        sys.exit(1)

