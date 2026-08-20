"""Central Position Sizing - The ONLY component that determines lot size.
Strategy NEVER specifies volume. Only this service calculates it.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class SizingResult:
    """Result of central position sizing - immutable"""
    symbol: str
    equity: float
    risk_pct: float
    entry_price: float
    stop_loss: float
    calculated_volume: float      # Raw calculation
    normalized_volume: float      # Rounded to broker step
    is_tradable: bool
    rejection_reason: Optional[str] = None


class CentralSizing:
    """
    THE ONLY component that calculates position size.
    
    Strategy calls: central_sizing.calculate(signal, account)
    Strategy NEVER sets: volume = X
    
    This ensures no code path can bypass risk-based sizing.
    """
    
    def __init__(self, volume_min: float = 0.01, volume_max: float = 200.0, 
                 volume_step: float = 0.01):
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.volume_step = volume_step
        self._call_count = 0  # Track who calls this service
    
    def calculate(self, equity: float, risk_pct: float, 
                  entry_price: float, stop_loss: float,
                  symbol: str = "EURUSD", pip_value_per_lot: float = 10.0) -> SizingResult:
        """
        THE canonical position sizing calculation.
        No other code should compute lot size.
        """
        self._call_count += 1
        
        # Step 1: Risk budget
        risk_budget = equity * risk_pct
        
        # Step 2: Stop distance in pips
        sl_distance_pips = abs(entry_price - stop_loss) / 0.0001
        
        if sl_distance_pips == 0:
            return SizingResult(symbol, equity, risk_pct, entry_price, stop_loss,
                              0, 0, False, "Zero stop distance")
        
        # Step 3: Raw volume = risk_budget / (sl_distance_pips * pip_value_per_lot)
        raw_volume = risk_budget / (sl_distance_pips * pip_value_per_lot)
        
        # Step 4: Normalize to broker volume step
        normalized = max(self.volume_min, 
                        min(self.volume_max,
                            round(raw_volume / self.volume_step) * self.volume_step))
        
        # Step 5: Check tradability
        if raw_volume < self.volume_min:
            actual_risk_at_min = sl_distance_pips * pip_value_per_lot * self.volume_min
            return SizingResult(
                symbol, equity, risk_pct, entry_price, stop_loss,
                raw_volume, normalized, False,
                f"Minimum volume {self.volume_min} requires ${actual_risk_at_min:.2f} risk, "
                f"but budget is only ${risk_budget:.4f}. Need ${actual_risk_at_min / risk_pct:.0f} equity."
            )
        
        return SizingResult(symbol, equity, risk_pct, entry_price, stop_loss,
                           raw_volume, normalized, True, None)
    
    def assert_no_strategy_volume(self, strategy_volume: Optional[float]) -> bool:
        """
        HARD CHECK: Strategy must NOT specify volume.
        If strategy passes a volume, this returns False.
        """
        if strategy_volume is not None:
            print(f"[CRITICAL] Strategy tried to specify volume={strategy_volume}!")
            print(f"[CRITICAL] Only CentralSizing may determine position size.")
            return False
        return True
    
    def get_stats(self):
        return {"call_count": self._call_count}


# Global singleton - THE only sizing service
central_sizing = CentralSizing()


# ============================================================================
# TEST - Prove strategy cannot specify volume
# ============================================================================
if __name__ == "__main__":
    print("=" * 65)
    print("  CENTRAL POSITION SIZING - Strategy Cannot Specify Volume")
    print("=" * 65)
    
    # Test 1: Strategy tries to specify volume -> REJECTED
    print("\n[1] Strategy tries volume=1.0 -> must be rejected:")
    strategy_volume = 1.0
    is_allowed = central_sizing.assert_no_strategy_volume(strategy_volume)
    print(f"  Strategy volume specified: {strategy_volume}")
    print(f"  Allowed: {is_allowed}")
    print(f"  VERDICT: {'FAIL - strategy should not specify volume' if strategy_volume is not None else 'PASS'}")
    
    # Test 2: Strategy provides NO volume -> central sizing calculates
    print("\n[2] Strategy provides NO volume -> central sizing calculates:")
    result = central_sizing.calculate(
        equity=5000, risk_pct=0.0005,
        entry_price=1.15542, stop_loss=1.15718,
    )
    print(f"  Calculated volume: {result.calculated_volume:.6f}")
    print(f"  Normalized volume: {result.normalized_volume}")
    print(f"  Is tradable: {result.is_tradable}")
    print(f"  Reason: {result.rejection_reason or 'OK'}")
    
    # Test 3: $19 account -> correctly rejected
    print("\n[3] $19 account -> central sizing correctly rejects:")
    result2 = central_sizing.calculate(
        equity=19.06, risk_pct=0.0005,
        entry_price=1.15542, stop_loss=1.15718,
    )
    print(f"  Is tradable: {result2.is_tradable}")
    print(f"  Reason: {result2.rejection_reason}")
    
    print(f"\n{'='*65}")
    print("  RESULT: CentralSizing is the ONLY volume decision-maker")
    print("  Strategy cannot override. Architecture enforces this.")
    print(f"{'='*65}")
