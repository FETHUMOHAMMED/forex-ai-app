import sys
sys.path.insert(0, '.')
from packages.risk.dual_risk_validation import validate_risk_before_order, validate_risk_after_fill

# $5000 account, 0.05% risk = $2.50 budget
pre = validate_risk_before_order(5000, 0.0005, 1.15542, 1.15718, 0.01, 10.0)
print("BEFORE ORDER:")
print(f"  SL distance: {pre.sl_distance_pips} pips")
print(f"  Risk: ${pre.actual_risk_usd:.2f} vs Budget: ${pre.risk_budget_usd:.2f}")
print(f"  SAFE: {pre.is_safe}")

# Actual fill moves entry 10 pips AWAY from SL (for SELL = entry goes DOWN)
actual_entry = 1.15442
post = validate_risk_after_fill(5000, 0.0005, actual_entry, 1.15718, 0.01, 10.0)
print()
print("AFTER FILL (entry moved 10 pips away from SL):")
print(f"  SL distance: {post.sl_distance_pips} pips")
print(f"  Risk: ${post.actual_risk_usd:.2f} vs Budget: ${post.risk_budget_usd:.2f}")
print(f"  SAFE: {post.is_safe}")

print()
if pre.is_safe and not post.is_safe:
    print("CRITICAL: Pre-order PASSED but post-fill FAILED!")
    print("This proves dual validation is ESSENTIAL")
elif not pre.is_safe:
    print("Pre-order already rejected (risk too high for this account)")
