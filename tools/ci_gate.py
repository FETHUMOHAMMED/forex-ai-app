"""CI GATE - Run all verification checks in sequence."""
import subprocess
import sys
from pathlib import Path

def run_check(name, command):
    """Run a check and report result."""
    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"{'='*70}")
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"  STDERR: {result.stderr[-200:]}")
    # Check BOTH returncode AND output for FAIL indicators
    success = result.returncode == 0
    if "FAIL" in result.stdout or "FAILED" in result.stdout:
        success = False
    if "EXECUTION PATH INCOMPLETE" in result.stdout:
        success = False
    return success

def main():
    """Run all CI checks."""
    print("="*70)
    print("  CI GATE - COMPLETE VERIFICATION")
    print("="*70)
    
    checks = [
        ("SAFETY SUITE", [sys.executable, "-m", "pytest", "tests/test_safety_suite.py", "-q"]),
        ("CANONICAL V4 AUDIT", [sys.executable, "tools/audit_canonical_v4.py"]),
        ("AST EXECUTION BOUNDARY", [sys.executable, "tools/enforce_execution_boundary_ast.py"]),
        ("SYNTHETIC SIGNAL TEST", [sys.executable, "tools/synthetic_signal_test.py"]),
    ("FULL-PATH ORCHESTRATION", [sys.executable, "tools/full_path_orchestration_test.py"]),
        ("RUNNER COUNT", [sys.executable, "tools/runner_count.py"]),
    ]
    
    results = []
    for name, command in checks:
        passed = run_check(name, command)
        results.append((name, passed))
    
    # Summary
    print(f"\n{'='*70}")
    print("  CI GATE SUMMARY")
    print(f"{'='*70}")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
    
    print(f"\n  RESULT: {passed}/{total} PASSED")
    
    if passed == total:
        print(f"\n  ? ALL CHECKS PASSED - Ready for next phase")
        return 0
    else:
        print(f"\n  ? {total-passed} CHECK(S) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())


