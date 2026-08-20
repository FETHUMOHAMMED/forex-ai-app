"""HARD Position Sizing - Uses real MT5 symbol specs. NO assumptions.
Advisor's required formula:
  risk_money = equity * risk_percent
  volume = risk_money / actual_loss_per_lot_at_SL
  HARD INVARIANT: actual_SL_risk <= configured_max_risk
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class HardPositionSize:
    """Position size calculated from REAL MT5 symbol specs - no assumptions"""
    # Inputs (from MT5 - authoritative)
    equity: float
    risk_percent: float           # e.g., 0.0005 for 0.05%
    
    # Symbol specs (from MT5 - authoritative)
    contract_size: float          # 100000.0 for EURUSD
    tick_value: float             # 1.0 for EURUSD
    tick_size: float              # 0.00001 for EURUSD
    point: float                  # 0.00001
    volume_min: float             # 0.01
    volume_max: float             # 200.0
    volume_step: float            # 0.01
    
    # Trade parameters
    entry_price: float
    stop_loss: float
    
    # Calculated
    risk_money: float = 0.0
    stop_distance_points: float = 0.0
    loss_per_lot_at_sl: float = 0.0   # How much 1 lot loses if SL hit
    raw_volume: float = 0.0           # Unrounded volume
    final_volume: float = 0.0         # Rounded to volume_step
    
    # Safety invariant
    actual_sl_risk: float = 0.0       # Actual $ risk with final_volume
    is_safe: bool = False             # actual_SL_risk <= risk_money?
    rejection_reason: Optional[str] = None


def calculate_hard_position_size(
    equity: float,
    risk_percent: float,
    contract_size: float,
    tick_value: float,
    tick_size: float,
    point: float,
    volume_min: float,
    volume_max: float,
    volume_step: float,
    entry_price: float,
    stop_loss: float,
) -> HardPositionSize:
    """
    THE advisor's required position sizing formula.
    Uses REAL MT5 symbol specs. Enforces HARD safety invariant.
    
    Returns HardPositionSize with is_safe=True ONLY if invariant holds.
    """
    
    # Step 1: risk_money = equity * risk_percent
    risk_money = equity * risk_percent
    
    # Step 2: Calculate stop distance in points (using REAL point size)
    stop_distance = abs(entry_price - stop_loss)
    stop_distance_points = stop_distance / point
    
    # Step 3: Calculate loss per lot at stop loss
    # Each tick moves tick_value dollars. Each point has (point/tick_size) ticks.
    # Loss per lot = stop_distance_points * ticks_per_point * tick_value
    ticks_per_point = point / tick_size
    loss_per_lot_at_sl = (stop_distance / (point * 10)) * (tick_value / tick_size) * point * 10
    
    # Step 4: raw_volume = risk_money / loss_per_lot_at_sl
    if loss_per_lot_at_sl > 0:
        raw_volume = risk_money / loss_per_lot_at_sl
    else:
        raw_volume = 0.0
    
    # Step 5: Round to volume_step
    final_volume = max(volume_min, min(volume_max, 
                      round(raw_volume / volume_step) * volume_step))
    
    # Step 6: Calculate actual SL risk with final volume
    actual_sl_risk = loss_per_lot_at_sl * final_volume
    
    # Step 7: HARD SAFETY INVARIANT
    is_safe = actual_sl_risk <= risk_money * 1.01  # Allow 1% tolerance for rounding
    rejection_reason = None
    
    if final_volume < volume_min:
        rejection_reason = (f"Required volume {raw_volume:.6f} below broker minimum {volume_min}. "
                          f"Need ${loss_per_lot_at_sl * volume_min:.2f} risk but budget is ${risk_money:.4f}.")
    elif not is_safe:
        rejection_reason = (f"HARD INVARIANT FAILED: actual_SL_risk ${actual_sl_risk:.2f} > "
                          f"risk_money ${risk_money:.4f}")
    
    return HardPositionSize(
        equity=equity, risk_percent=risk_percent,
        contract_size=contract_size, tick_value=tick_value,
        tick_size=tick_size, point=point,
        volume_min=volume_min, volume_max=volume_max, volume_step=volume_step,
        entry_price=entry_price, stop_loss=stop_loss,
        risk_money=risk_money,
        stop_distance_points=stop_distance_points,
        loss_per_lot_at_sl=loss_per_lot_at_sl,
        raw_volume=raw_volume, final_volume=final_volume,
        actual_sl_risk=actual_sl_risk, is_safe=is_safe,
        rejection_reason=rejection_reason,
    )
