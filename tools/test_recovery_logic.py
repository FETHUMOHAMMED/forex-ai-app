"""Test graceful recovery: HALT -> 3 healthy -> READY"""
import sys
sys.path.insert(0, '.')
from packages.integrity.continuous_scanner import ContinuousScanner

scanner = ContinuousScanner()

# Simulate: HALT (1 failure)
result_halt = {"overall": "HALT", "timestamp": "test"}
state1 = scanner.evaluate_state(result_halt)
print(f"After HALT: state={state1}, healthy={scanner.consecutive_healthy}")

# Simulate: 3 consecutive healthy scans
for i in range(3):
    result_ready = {"overall": "READY", "timestamp": "test"}
    state = scanner.evaluate_state(result_ready)
    print(f"Healthy scan {i+1}: state={state}, healthy={scanner.consecutive_healthy}")

print(f"\nRecovery status: {scanner.get_recovery_status()}")
print(f"RESULT: {'CORRECT - 3 scans needed, then READY' if scanner.state == 'READY' else 'INCORRECT'}")
