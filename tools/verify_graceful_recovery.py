"""Verify Graceful Recovery - All advisor requirements"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.integrity.continuous_scanner import ContinuousScanner

print("=" * 70)
print("  GRACEFUL RECOVERY - ADVISOR VERIFICATION")
print("=" * 70)

# Advisor's requirements:
# 1. HALT on failure
# 2. NO immediate resume after 1 healthy scan
# 3. 3 consecutive healthy scans required
# 4. Recovery counter resets on failure

scanner = ContinuousScanner()

print("\n  ADVISOR REQUIREMENTS:")

# Test 1: HALT on critical failure
print("\n  [TEST 1] Critical failure -> HALT")
result_halt = {"overall": "HALT", "timestamp": "test"}
state = scanner.evaluate_state(result_halt)
test1 = state == "HALT"
print(f"  Result: {state}")
print(f"  Expected: HALT")
print(f"  PASS: {test1}")

# Test 2: 1 healthy scan should NOT resume (should be RECOVERING)
print("\n  [TEST 2] 1 healthy scan -> NOT READY (RECOVERING)")
result_ready = {"overall": "READY", "timestamp": "test"}
state = scanner.evaluate_state(result_ready)
test2 = state == "RECOVERING"
print(f"  Result: {state}")
print(f"  Expected: RECOVERING (not READY)")
print(f"  PASS: {test2}")

# Test 3: 2nd healthy scan -> still RECOVERING
print("\n  [TEST 3] 2nd healthy scan -> still RECOVERING")
state = scanner.evaluate_state(result_ready)
test3 = state == "RECOVERING"
print(f"  Result: {state}")
print(f"  Expected: RECOVERING")
print(f"  PASS: {test3}")

# Test 4: 3rd healthy scan -> READY
print("\n  [TEST 4] 3rd healthy scan -> READY")
state = scanner.evaluate_state(result_ready)
test4 = state == "READY"
print(f"  Result: {state}")
print(f"  Expected: READY")
print(f"  PASS: {test4}")

# Test 5: Failure during recovery resets counter
print("\n  [TEST 5] Failure during recovery -> HALT + reset")
# Simulate recovery then failure
scanner2 = ContinuousScanner()
scanner2.evaluate_state({"overall": "HALT", "timestamp": "test"})
scanner2.evaluate_state({"overall": "READY", "timestamp": "test"})  # 1/3
scanner2.evaluate_state({"overall": "READY", "timestamp": "test"})  # 2/3
# Now fail!
scanner2.evaluate_state({"overall": "HALT", "timestamp": "test"})
test5 = scanner2.state == "HALT" and scanner2.consecutive_healthy == 0
print(f"  State: {scanner2.state}")
print(f"  Healthy counter: {scanner2.consecutive_healthy}")
print(f"  Expected: HALT, counter reset to 0")
print(f"  PASS: {test5}")

# Test 6: Recovery threshold is 3
print("\n  [TEST 6] Recovery threshold = 3")
test6 = scanner2.recovery_required == 3
print(f"  Threshold: {scanner2.recovery_required}")
print(f"  Expected: 3")
print(f"  PASS: {test6}")

# Test 7: State history tracking
print("\n  [TEST 7] State transitions tracked")
test7 = hasattr(scanner, 'state_history')
print(f"  History attribute: {test7}")
print(f"  PASS: {test7}")

# Summary
print(f"\n{'='*70}")
results = [test1, test2, test3, test4, test5, test6, test7]
passed = sum(results)
print(f"  RESULT: {passed}/{len(results)} TESTS PASSED")

if passed == 7:
    print(f"  VERDICT: GRACEFUL RECOVERY FULLY IMPLEMENTED")
    print(f"    - HALT on failure: YES")
    print(f"    - No immediate resume: YES (RECOVERING state)")
    print(f"    - 3 consecutive scans: YES")
    print(f"    - Counter resets on failure: YES")
    print(f"    - Threshold = 3: YES")
else:
    print(f"  VERDICT: ISSUES FOUND")
print("=" * 70)
