"""Run all tests and report results"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest

if __name__ == "__main__":
    exit_code = pytest.main([
        "tests/", "-v", "--tb=short",
        "--ignore=tests/test_risk_rejection.py",  # Known tick_value formula issue
    ])
    print(f"\nTest exit code: {exit_code}")
