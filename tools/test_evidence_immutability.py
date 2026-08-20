"""Test: Evidence record detects mutation."""
import sys
sys.path.insert(0, '.')
from packages.execution.trade_evidence import TradeEvidenceRecord

# Create evidence record
evidence = TradeEvidenceRecord(
    signal_id="SIG_TEST",
    account_id=REDACTED_LIVE_ACCOUNT,
    MT5_login=REDACTED_LIVE_ACCOUNT,
    strategy_version="V3_REGIME",
    model_version="v1.0",
    signal_time="2026-08-18T10:00:00+00:00",
    execution_attempt_time="2026-08-18T10:00:14+00:00",
    planned_entry=1.15542,
    planned_sl=1.15718,
    planned_tp=1.15261,
    volume=0.01,
)

print("=" * 60)
print("  EVIDENCE IMMUTABILITY TEST")
print("=" * 60)

print(f"\n  1. Original record:")
print(f"     Entry: {evidence.planned_entry}")
print(f"     Hash:  {evidence.evidence_hash}")
print(f"     Verify: {evidence.verify_integrity()}")

# Try to mutate (should be detected)
print(f"\n  2. Attempting mutation:")
try:
    evidence.planned_entry = 1.16000  # Try to change entry
    print(f"     Mutation succeeded (entry changed)")
    print(f"     Verify: {evidence.verify_integrity()}")
except Exception as e:
    print(f"     Mutation blocked: {e}")

# Check if hash still matches original
print(f"\n  3. Integrity check:")
print(f"     Verify: {evidence.verify_integrity()}")

if evidence.verify_integrity():
    print(f"     RESULT: IMMUTABLE (mutation prevented)")
else:
    print(f"     RESULT: TAMPERED (mutation detected)")
print("=" * 60)
