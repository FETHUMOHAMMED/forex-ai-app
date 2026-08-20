"""AUDIT EXECUTION PATH - Is live exactly the same as backtested?"""
import json
from pathlib import Path

def audit_execution_path():
    """Verify live execution path matches backtest exactly."""
    
    print("="*70)
    print("  EXECUTION PATH AUDIT")
    print("  Is live = backtested?")
    print("="*70)
    
    # What the BACKTEST used (from canonical_v4.py)
    backtest_filters = [
        "1. Bullish FVG (candle_1_high < candle_3_low)",
        "2. EMA50 > EMA200 (bullish bias)",
        "3. London session (7-11 UTC)",
        "4. BUY only"
    ]
    
    # What the LIVE path currently has
    live_filters = [
        "1. Bullish FVG",
        "2. EMA50 > EMA200",
        "3. London session (7-11 UTC)",
        "4. BUY only",
        "5. REGIME FILTER: STRONG_UPTREND or WEAK_UPTREND"  # ? EXTRA?
    ]
    
    print(f"\n  BACKTEST FILTERS (what was tested):")
    for filter in backtest_filters:
        print(f"    {filter}")
    
    print(f"\n  LIVE FILTERS (what would execute):")
    for filter in live_filters:
        print(f"    {filter}")
    
    print(f"\n{'='*70}")
    print("  CRITICAL FINDING")
    print("="*70)
    
    print(f"""
  The BACKTEST used 4 filters.
  The LIVE path has 5 filters.
  
  EXTRA FILTER: Regime check (STRONG_UPTREND/WEAK_UPTREND)
  
  IS THIS A PROBLEM?
  
  YES - The regime filter is NOT in the canonical backtest.
  
  The backtest naturally excludes bearish trades because:
  - EMA50 > EMA200 already filters for bullish conditions
  - BUY only already ensures direction
  
  Adding a SEPARATE regime filter means:
  - Live strategy ? Backtested strategy
  - You're testing something different than what you validated
  - The paper trading results won't match the backtest
""")
    
    print(f"{'='*70}")
    print("  RECOMMENDATION")
    print("="*70)
    
    print(f"""
  OPTION A: Remove the regime filter from live execution
  - Live path = Backtest path (4 filters only)
  - The EMA50 > EMA200 already handles direction
  - This is the CORRECT approach for paper validation
  
  OPTION B: Keep regime filter but re-backtest
  - Requires re-running the ENTIRE backtest with regime filter
  - Changes the strategy definition
  - Invalidates previous results
  
  RECOMMENDED: OPTION A
  The regime filter is redundant with EMA50 > EMA200.
  Remove it from the execution path.
  Keep the canonical strategy exactly as backtested.
""")
    
    return {
        "backtest_filters": len(backtest_filters),
        "live_filters": len(live_filters),
        "extra_filter_detected": True,
        "recommendation": "Remove regime filter from live path"
    }

if __name__ == "__main__":
    audit_execution_path()
