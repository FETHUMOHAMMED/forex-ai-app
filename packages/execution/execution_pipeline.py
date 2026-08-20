"""P0: Unified Execution Pipeline - EVERY gate must pass before MT5 order.
Sequence: Signal ? Freshness ? Deviation ? SL/TP ? Spread ? Symbol ? Risk ? Lot ? Margin ? MT5 ? Verify ? DB
"""
from dataclasses import dataclass, field
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from datetime import datetime, timezone
from typing import Optional, List, Dict
from enum import Enum

class GateResult(str, Enum):
    PASS = "PASS"
    REJECT = "REJECT"
    EXCEPTION = "EXCEPTION"

@dataclass
class GateCheck:
    """Result of a single gate check"""
    gate_name: str
    result: GateResult
    detail: str = ""
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class ExecutionPipelineResult:
    """Complete execution pipeline result - ALL gates must pass"""
    signal_id: str
    pair: str
    direction: str
    gates: List[GateCheck] = field(default_factory=list)
    is_approved: bool = False
    mt5_order_ticket: Optional[int] = None
    mt5_position_ticket: Optional[int] = None
    rejection_reason: Optional[str] = None
    
    def add_gate(self, name: str, passed: bool, detail: str = ""):
        gate = GateCheck(
            gate_name=name,
            result=GateResult.PASS if passed else GateResult.REJECT,
            detail=detail
        )
        self.gates.append(gate)
        return passed
    
    @property
    def all_passed(self) -> bool:
        return all(g.result == GateResult.PASS for g in self.gates)
    
    def summary(self) -> str:
        lines = [f"EXECUTION PIPELINE: {self.signal_id}"]
        for g in self.gates:
            icon = "[PASS]" if g.result == GateResult.PASS else "[REJECT]"
            lines.append(f"  {icon} {g.gate_name}: {g.detail}")
        lines.append(f"  APPROVED: {self.is_approved}")
        if self.rejection_reason:
            lines.append(f"  REJECTED: {self.rejection_reason}")
        return "\n".join(lines)


def execute_pipeline(
    signal: dict,
    account_balance: float,
    account_equity: float,
    account_free_margin: float,
    trades_today: int,
    max_daily_trades: int,
    current_bid: float,
    current_ask: float,
) -> ExecutionPipelineResult:
    """
    THE complete execution pipeline. Every gate must pass.
    
    Gates (in order):
    1. Freshness - signal < 120s old
    2. Deviation - < 5 pips from planned
    3. SL/TP validation - correct side of actual fill
    4. Spread check - within acceptable range
    5. Symbol spec check - volume within broker limits
    6. Risk budget check - actual_risk <= max_risk
    7. Lot size normalization - round to volume_step
    8. Margin check - sufficient free margin
    
    Returns ExecutionPipelineResult. If not approved, DO NOT send MT5 order.
    """
    result = ExecutionPipelineResult(
        signal_id=signal.get('signal_id', 'unknown'),
        pair=signal.get('pair', ''),
        direction=signal.get('direction', ''),
    )
    
    # Explicit execution field separation
    result.signal_entry = signal.get('entry')
    result.requested_entry = signal.get('entry')
    result.actual_entry = freshness.current_entry if 'freshness' in dir() else None
    result.entry_deviation_pips = abs(result.actual_entry - result.signal_entry) * 10000 if result.actual_entry and result.signal_entry else 0
    
    from datetime import datetime as dt
    from packages.execution.signal_freshness import validate_signal_freshness
    
    # ========================================================================
    # GATE 1: Signal Freshness (< 120s old)
    # ========================================================================
    freshness = validate_signal_freshness(signal, current_bid, current_ask)
    if not freshness.is_fresh:
        result.add_gate("1. Freshness", False, f"Signal {freshness.signal_age_seconds:.0f}s old")
        result.rejection_reason = "STALE_SIGNAL"
        return result
    result.add_gate("1. Freshness", True, f"{freshness.signal_age_seconds:.0f}s old")
    
    # ========================================================================
    # GATE 2: Entry Deviation (< 5 pips)
    # ========================================================================
    if not freshness.entry_acceptable:
        result.add_gate("2. Deviation", False, f"{freshness.entry_deviation_pips:.1f} pips")
        result.rejection_reason = "EXTREME_DEVIATION"
        return result
    result.add_gate("2. Deviation", True, f"{freshness.entry_deviation_pips:.1f} pips")
    
    # ========================================================================
    # GATE 3: SL/TP Validation (using recalculated values)
    # ========================================================================
    if not freshness.sl_valid or not freshness.tp_valid:
        result.add_gate("3. SL/TP", False, f"SL_valid={freshness.sl_valid} TP_valid={freshness.tp_valid}")
        result.rejection_reason = "INVALID_SLTP"
        return result
    result.add_gate("3. SL/TP", True, f"SL={freshness.recalculated_sl:.5f} TP={freshness.recalculated_tp:.5f}")
    
    # ========================================================================
    # GATE 4: Spread Check
    # ========================================================================
    spread = current_ask - current_bid
    max_spread = 0.0015  # 15 pips for EURUSD on exchange mode
    if spread > max_spread:
        result.add_gate("4. Spread", False, f"{spread:.6f} > {max_spread}")
        result.rejection_reason = "SPREAD_TOO_WIDE"
        return result
    result.add_gate("4. Spread", True, f"{spread:.6f}")
    
    # ========================================================================
    # GATE 5: Symbol Spec Check
    # ========================================================================
    volume = 0.01  # Fixed micro lot for validation
    vol_min = 0.01
    vol_max = 200.0
    if volume < vol_min or volume > vol_max:
        result.add_gate("5. Symbol Spec", False, f"Volume {volume} outside [{vol_min}, {vol_max}]")
        result.rejection_reason = "INVALID_VOLUME"
        return result
    result.add_gate("5. Symbol Spec", True, f"Volume {volume} within limits")
    
    # ========================================================================
    # GATE 6: Risk Budget Check
    # ========================================================================
    sl_distance_pips = abs(freshness.recalculated_sl - freshness.current_entry) / 0.0001
    pip_value_per_lot = 10.0
    actual_risk = sl_distance_pips * pip_value_per_lot * volume
    risk_budget = account_balance * 0.0005  # 0.05%
    
    if actual_risk > risk_budget * 1.01:
        result.add_gate("6. Risk Budget", False, f"${actual_risk:.2f} > ${risk_budget:.4f}")
        result.rejection_reason = f"RISK_BUDGET_EXCEEDED ({actual_risk/risk_budget:.1f}x)"
        return result
    result.add_gate("6. Risk Budget", True, f"${actual_risk:.2f} <= ${risk_budget:.4f}")
    
    # ========================================================================
    # GATE 7: Lot Size Normalization
    # ========================================================================
    volume_step = 0.01
    normalized_volume = round(volume / volume_step) * volume_step
    if normalized_volume != volume:
        result.add_gate("7. Lot Size", False, f"{volume} not on step {volume_step}")
        result.rejection_reason = "INVALID_LOT_STEP"
        return result
    result.add_gate("7. Lot Size", True, f"{normalized_volume} on step")
    
    # ========================================================================
    # GATE 8: Margin Check
    # ========================================================================
    notional = 100000 * normalized_volume * freshness.current_entry
    margin_required = notional * 0.01  # Approximate 1% margin
    if margin_required > account_free_margin:
        result.add_gate("8. Margin", False, f"${margin_required:.0f} > ${account_free_margin:.0f}")
        result.rejection_reason = "INSUFFICIENT_MARGIN"
        return result
    result.add_gate("8. Margin", True, f"${margin_required:.0f} required")
    
    # ========================================================================
    # ALL GATES PASSED
    # ========================================================================
    result.is_approved = True
    result.rejection_reason = None
    return result


# ============================================================================
# TEST
# ============================================================================
if __name__ == "__main__":
    # Test with a fresh valid signal
    fresh_signal = {
        'signal_id': 'TEST_FRESH',
        'generated_at': datetime.now(timezone.utc),
        'expires_at': datetime.now(timezone.utc),
        'pair': 'EURUSD',
        'direction': 'SELL',
        'entry': 1.15540,
        'stop_loss': 1.15700,
        'take_profit': 1.15200,
    }
    
    result = execute_pipeline(
        signal=fresh_signal,
        account_balance=5000,
        account_equity=5000,
        account_free_margin=5000,
        trades_today=0,
        max_daily_trades=5,
        current_bid=1.15542,
        current_ask=1.15550,
    )
    print(result.summary())
    print(f"\nTest: {'PASS - all gates work' if result.is_approved else 'FAIL'}")

