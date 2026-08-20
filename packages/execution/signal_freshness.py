"""P0: Signal Freshness Gate - Prevents stale signal execution.
The root cause of ID 163: stale cached signal (1.15123) executed at wrong price (1.15542).
This gate ensures signals are fresh and SL/TP are recalculated for current market price.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

MAX_SIGNAL_AGE_SECONDS = 120  # Signal must be < 2 minutes old
MAX_ENTRY_DEVIATION_PIPS = 5.0  # Max allowed deviation from signal to fill

@dataclass
class SignalFreshness:
    """Validates a signal is fresh and executable at current market price"""
    signal_id: str
    signal_generated_at: datetime
    signal_expires_at: datetime
    pair: str
    direction: str
    
    # Planned (from signal)
    planned_entry: float
    planned_sl: float
    planned_tp: float
    
    # Current market (from MT5 tick)
    current_bid: float
    current_ask: float
    
    # Computed
    signal_age_seconds: float = 0.0
    is_fresh: bool = False
    current_entry: float = 0.0  # bid for SELL, ask for BUY
    entry_deviation_pips: float = 0.0
    entry_acceptable: bool = False
    
    # Recalculated SL/TP for current market
    recalculated_sl: float = 0.0
    recalculated_tp: float = 0.0
    sl_valid: bool = False
    tp_valid: bool = False
    
    issues: list = field(default_factory=list)
    
    def __post_init__(self):
        now = datetime.now(timezone.utc)
        self.signal_age_seconds = (now - self.signal_generated_at).total_seconds()
        self.is_fresh = self.signal_age_seconds < MAX_SIGNAL_AGE_SECONDS
        
        # Current entry price based on direction
        self.current_entry = self.current_bid if self.direction == 'SELL' else self.current_ask
        
        # Entry deviation from planned
        self.entry_deviation_pips = abs(self.current_entry - self.planned_entry) * 10000
        self.entry_acceptable = self.entry_deviation_pips <= MAX_ENTRY_DEVIATION_PIPS
        
        # Recalculate SL/TP distances from planned signal
        sl_distance = abs(self.planned_sl - self.planned_entry)
        tp_distance = abs(self.planned_tp - self.planned_entry)
        
        # Apply same distances to current market price
        if self.direction == 'SELL':
            self.recalculated_sl = self.current_entry + sl_distance  # SL above entry
            self.recalculated_tp = self.current_entry - tp_distance  # TP below entry
            self.sl_valid = self.recalculated_sl > self.current_entry
            self.tp_valid = self.recalculated_tp < self.current_entry
        else:  # BUY
            self.recalculated_sl = self.current_entry - sl_distance  # SL below entry
            self.recalculated_tp = self.current_entry + tp_distance  # TP above entry
            self.sl_valid = self.recalculated_sl < self.current_entry
            self.tp_valid = self.recalculated_tp > self.current_entry
        
        # Collect issues
        if not self.is_fresh:
            self.issues.append(f"STALE_SIGNAL: {self.signal_age_seconds:.0f}s old (max {MAX_SIGNAL_AGE_SECONDS}s)")
        if not self.entry_acceptable:
            self.issues.append(f"EXTREME_DEVIATION: {self.entry_deviation_pips:.1f} pips from planned (max {MAX_ENTRY_DEVIATION_PIPS})")
        if not self.sl_valid:
            self.issues.append(f"SL_INVALID: recalculated SL {self.recalculated_sl:.5f} vs entry {self.current_entry:.5f}")
        if not self.tp_valid:
            self.issues.append(f"TP_INVALID: recalculated TP {self.recalculated_tp:.5f} vs entry {self.current_entry:.5f}")
    
    @property
    def is_executable(self) -> bool:
        """Signal is fresh AND SL/TP are valid for current market"""
        return self.is_fresh and self.entry_acceptable and self.sl_valid and self.tp_valid
    
    def summary(self) -> str:
        lines = [
            f"SIGNAL FRESHNESS CHECK",
            f"  Signal ID: {self.signal_id}",
            f"  Age: {self.signal_age_seconds:.0f}s (max {MAX_SIGNAL_AGE_SECONDS}s) -> {'FRESH' if self.is_fresh else 'STALE'}",
            f"  Planned Entry: {self.planned_entry:.5f}",
            f"  Current Market: {self.current_entry:.5f} ({self.direction})",
            f"  Deviation: {self.entry_deviation_pips:.1f} pips -> {'OK' if self.entry_acceptable else 'EXTREME'}",
            f"  Recalculated SL: {self.recalculated_sl:.5f} -> {'VALID' if self.sl_valid else 'INVALID'}",
            f"  Recalculated TP: {self.recalculated_tp:.5f} -> {'VALID' if self.tp_valid else 'INVALID'}",
            f"  EXECUTABLE: {self.is_executable}",
        ]
        if self.issues:
            lines.append(f"  ISSUES: {'; '.join(self.issues)}")
        return "\n".join(lines)


def validate_signal_freshness(signal: dict, current_bid: float, current_ask: float) -> SignalFreshness:
    """
    P0: Validate signal freshness and recalculate SL/TP for current market.
    MUST be called immediately before order placement.
    If not executable, DO NOT SEND ORDER.
    """
    return SignalFreshness(
        signal_id=signal.get('signal_id', 'unknown'),
        signal_generated_at=signal.get('generated_at', datetime.now(timezone.utc)),
        signal_expires_at=signal.get('expires_at', datetime.now(timezone.utc)),
        pair=signal['pair'],
        direction=signal['direction'],
        planned_entry=signal['entry'],
        planned_sl=signal['stop_loss'],
        planned_tp=signal['take_profit'],
        current_bid=current_bid,
        current_ask=current_ask,
    )
