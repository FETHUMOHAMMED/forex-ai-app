"""Test the advisor's exact example: $19 account, 0.05%, 17.6 pip SL"""
import sys
sys.path.insert(0, '.')
from packages.integrity.risk.deep_health import calculate_risk_evidence

# Advisor's example
evidence = calculate_risk_evidence(
    equity=19.00,
    risk_pct=0.0005,
    entry=1.15542,
    sl=1.15718,
    volume=0.01,
)

print("=" * 65)
print("  RISK GATE - ADVISOR'S EXAMPLE")
print("=" * 65)
print(f"  Equity:          ${evidence.equity:.2f}")
print(f"  Risk:            {evidence.risk_pct*100:.2f}%")
print(f"  Budget:          ${evidence.budget:.4f}")
print(f"  Entry:           {evidence.entry}")
print(f"  SL:              {evidence.sl}")
print(f"  Actual risk:     ${evidence.actual_risk:.2f}")
print(f"  Risk ratio:      {evidence.risk_ratio:.2f}x")
print(f"  RESULT:          {'HALT' if not evidence.is_safe else 'SAFE'}")
print("=" * 65)
