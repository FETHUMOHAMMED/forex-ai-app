"""HISTORICAL FUNNEL - Real empirical joint frequency, not multiplication."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from packages.strategy.canonical_v4 import CanonicalV4Strategy

def historical_funnel():
    """Compute the ACTUAL historical funnel from 8 years of data."""
    print("="*70)
    print("  HISTORICAL V4 FUNNEL (Empirical, Not Theoretical)")
    print("="*70)
    
    strategy = CanonicalV4Strategy()
    data = strategy.load_data(bars=10000)
    data = strategy.generate_features(data)
    
    n = len(data)
    
    # Compute each stage empirically
    london_mask = data['in_session'] == True
    bullish_mask = data['bullish_bias'] == True
    fvg_mask = data['bullish_fvg'] == True
    signal_mask = data['signal'] == True
    
    london_count = london_mask.sum()
    bullish_count = bullish_mask.sum()
    fvg_count = fvg_mask.sum()
    signal_count = signal_mask.sum()
    
    # Joint conditions
    london_bullish = (london_mask & bullish_mask).sum()
    london_fvg = (london_mask & fvg_mask).sum()
    bullish_fvg = (bullish_mask & fvg_mask).sum()
    all_three = (london_mask & bullish_mask & fvg_mask).sum()
    
    print(f"\n  HISTORICAL SAMPLE: {n} H4 bars")
    print(f"  Period: {data['timestamp'].min()} to {data['timestamp'].max()}")
    
    print(f"\n  INDIVIDUAL CONDITIONS:")
    print(f"    London session:   {london_count:>5} ({london_count/n*100:>5.1f}%)")
    print(f"    Bullish bias:     {bullish_count:>5} ({bullish_count/n*100:>5.1f}%)")
    print(f"    FVG detected:     {fvg_count:>5} ({fvg_count/n*100:>5.1f}%)")
    
    print(f"\n  JOINT CONDITIONS (EMPIRICAL):")
    print(f"    London + Bullish: {london_bullish:>5} ({london_bullish/n*100:>5.2f}%)")
    print(f"    London + FVG:     {london_fvg:>5} ({london_fvg/n*100:>5.2f}%)")
    print(f"    Bullish + FVG:    {bullish_fvg:>5} ({bullish_fvg/n*100:>5.2f}%)")
    print(f"    All three:        {all_three:>5} ({all_three/n*100:>5.2f}%)")
    
    print(f"\n  THE V4 SIGNAL (the real requirement):")
    print(f"    Signals:          {signal_count:>5} ({signal_count/n*100:>5.2f}%)")
    
    # Compare with theoretical multiplication
    theoretical = (london_count/n) * (bullish_count/n) * (fvg_count/n)
    empirical = all_three / n
    
    print(f"\n  INDEPENDENCE TEST:")
    print(f"    Theoretical (if independent): {theoretical*100:.2f}%")
    print(f"    Empirical (actual):           {empirical*100:.2f}%")
    print(f"    Ratio:                        {empirical/theoretical:.2f}x")
    
    if empirical > theoretical * 1.2:
        print(f"    ? Conditions are POSITIVELY correlated")
    elif empirical < theoretical * 0.8:
        print(f"    ? Conditions are NEGATIVELY correlated")
    else:
        print(f"    ? Conditions are approximately independent")
    
    # The REAL expected setup rate
    print(f"\n  {'='*70}")
    print(f"  THE REAL EXPECTED SETUP RATE")
    print(f"  {'='*70}")
    print(f"\n  Historical: {all_three} valid setups in {n} bars")
    print(f"  Rate: {all_three/n*100:.2f}%")
    print(f"  Per year (2080 H4 bars): {all_three/n*2080:.1f} setups")
    print(f"  Per month: {all_three/n*2080/12:.1f} setups")
    
    # Per-bar funnel
    print(f"\n  CONDITIONAL FUNNEL:")
    print(f"    {n:>5} H4 bars")
    print(f"    ? {london_count:>5} London ({london_count/n*100:.1f}%)")
    print(f"    ? {london_bullish:>5} London + Bullish ({london_bullish/n*100:.1f}% of all)")
    print(f"    ? {all_three:>5} London + Bullish + FVG ({all_three/n*100:.2f}% of all)")
    print(f"    ? {signal_count:>5} V4 signals")
    
    # Conditional probabilities
    print(f"\n  CONDITIONAL PROBABILITIES:")
    if london_count > 0:
        print(f"    P(Bullish | London) = {london_bullish/london_count*100:.1f}%")
        print(f"    P(FVG | London + Bullish) = {all_three/london_bullish*100:.1f}%")
        print(f"    P(V4 | London) = {signal_count/london_count*100:.1f}%")

if __name__ == "__main__":
    historical_funnel()
