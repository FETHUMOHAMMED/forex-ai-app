"""Dual Risk Validation - Risk checked BEFORE order AND AFTER actual fill.
Actual execution price changes risk geometry, so we must re-validate.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

@dataclass(frozen=True)
class RiskSnapshot:
    """One risk assessment at a specific point"""
    point: str  # "BEFORE_ORDER" or "AFTER_FILL"
    equity: float
    risk_pct: float
    risk_budget_usd: float
    entry_price: float
    stop_loss: float
    sl_distance_pips: float
    volume: float
    pip_value_per_lot: float
    actual_risk_usd: float
    is_safe: bool
    timestamp_utc: str

def validate_risk_before_order(
    equity: float,
    risk_pct: float,
    planned_entry: float,
    planned_sl: float,
    volume: float,
    pip_value_per_lot: float = 10.0,
) -> RiskSnapshot:
    """
    RISK CHECK #1: BEFORE ORDER SUBMISSION.
    Uses PLANNED prices. Rejects if risk exceeds budget.
    """
    risk_budget = equity * risk_pct
    sl_distance_pips = abs(planned_entry - planned_sl) / 0.0001
    actual_risk = sl_distance_pips * pip_value_per_lot * volume
    
    return RiskSnapshot(
        point="BEFORE_ORDER",
        equity=equity,
        risk_pct=risk_pct,
        risk_budget_usd=round(risk_budget, 4),
        entry_price=planned_entry,
        stop_loss=planned_sl,
        sl_distance_pips=round(sl_distance_pips, 1),
        volume=volume,
        pip_value_per_lot=pip_value_per_lot,
        actual_risk_usd=round(actual_risk, 2),
        is_safe=actual_risk <= risk_budget * 1.01,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )

def validate_risk_after_fill(
    equity: float,
    risk_pct: float,
    actual_entry: float,
    actual_sl: float,
    actual_volume: float,
    pip_value_per_lot: float = 10.0,
) -> RiskSnapshot:
    """
    RISK CHECK #2: AFTER ACTUAL FILL.
    Uses ACTUAL execution prices. Can FAIL even if pre-order passed.
    Example: Pre-order planned SL=17.6 pips. Actual fill moves entry 5 pips 
    closer to SL -> actual SL distance = 12.6 pips -> LESS risk.
    But if entry moves 5 pips AWAY from SL -> actual SL = 22.6 pips -> MORE risk!
    """
    risk_budget = equity * risk_pct
    sl_distance_pips = abs(actual_entry - actual_sl) / 0.0001
    actual_risk = sl_distance_pips * pip_value_per_lot * actual_volume
    
    return RiskSnapshot(
        point="AFTER_FILL",
        equity=equity,
        risk_pct=risk_pct,
        risk_budget_usd=round(risk_budget, 4),
        entry_price=actual_entry,
        stop_loss=actual_sl,
        sl_distance_pips=round(sl_distance_pips, 1),
        volume=actual_volume,
        pip_value_per_lot=pip_value_per_lot,
        actual_risk_usd=round(actual_risk, 2),
        is_safe=actual_risk <= risk_budget * 1.01,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )


# ============================================================================
# TEST - Prove dual validation catches risk changes
# ============================================================================
if __name__ == "__main__":
    print("=" * 65)
    print("  DUAL RISK VALIDATION TEST")
    print("=" * 65)
    
    # Scenario: Planned entry 1.15542, SL 1.15718 (17.6 pips)
    # But actual fill is 1.15700 (only 1.8 pips from SL!)
    print("\n  SCENARIO: Planned entry fills 15.8 pips higher")
    print("  Planned: Entry=1.15542 SL=1.15718 (17.6 pips SL)")
    print("  Actual:  Entry=1.15700 SL=1.15718 (1.8 pips SL!)")
    print()
    
    # PRE-ORDER CHECK (with planned prices)
    pre = validate_risk_before_order(
        equity=19.06, risk_pct=0.0005,
        planned_entry=1.15542, planned_sl=1.15718,
        volume=0.01, pip_value_per_lot=10.0,
    )
    print(f"  [BEFORE ORDER]")
    print(f"    SL distance: {pre.sl_distance_pips} pips")
    print(f"    Risk: ${pre.actual_risk_usd:.2f}")
    print(f"    Budget: ${pre.risk_budget_usd:.4f}")
    print(f"    SAFE: {pre.is_safe}")
    
    # POST-FILL CHECK (with actual prices)
    post = validate_risk_after_fill(
        equity=19.06, risk_pct=0.0005,
        actual_entry=1.15700, actual_sl=1.15718,
        actual_volume=0.01, pip_value_per_lot=10.0,
    )
    print(f"\n  [AFTER FILL]")
    print(f"    SL distance: {post.sl_distance_pips} pips")
    print(f"    Risk: ${post.actual_risk_usd:.2f}")
    print(f"    Budget: ${post.risk_budget_usd:.4f}")
    print(f"    SAFE: {post.is_safe}")
    
    print(f"\n  RESULT:")
    if pre.is_safe and not post.is_safe:
        print(f"    Pre-order PASSED but post-fill FAILED!")
        print(f"    Risk changed from {pre.sl_distance_pips} pips to {post.sl_distance_pips} pips")
        print(f"    This is exactly why dual validation is CRITICAL")
    else:
        print(f"    Both checks consistent")
    
    print(f"\n{'='*65}")
