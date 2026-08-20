import sys
sys.path.insert(0, '.')
from packages.risk.hard_position_size import calculate_hard_position_size

# Real EURUSDm specs from MT5 + Live_Micro account
result = calculate_hard_position_size(
    equity=19.06,
    risk_percent=0.0005,
    contract_size=100000.0,
    tick_value=1.0,
    tick_size=0.00001,
    point=0.00001,
    volume_min=0.01,
    volume_max=200.0,
    volume_step=0.01,
    entry_price=1.15542,
    stop_loss=1.15718,
)

print("=== HARD POSITION SIZE (Real MT5 Specs) ===")
print(f"Risk Money: ${result.risk_money:.4f}")
print(f"Stop Distance: {result.stop_distance_points:.0f} points")
print(f"Loss Per Lot at SL: ${result.loss_per_lot_at_sl:.2f}")
print(f"Raw Volume: {result.raw_volume:.6f}")
print(f"Final Volume: {result.final_volume:.2f}")
print(f"Actual SL Risk: ${result.actual_sl_risk:.2f}")
print(f"HARD INVARIANT SAFE: {result.is_safe}")
if result.rejection_reason:
    print(f"REJECTED: {result.rejection_reason}")
    
# Also test: what equity IS needed for 0.05% risk with 0.01 lots?
needed_equity = result.loss_per_lot_at_sl * 0.01 / 0.0005
print(f"\nEquity needed for 0.01 lot, 0.05pct risk: ${needed_equity:,.0f}")
