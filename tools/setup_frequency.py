"""SETUP FREQUENCY - Conditional probability structure."""
import json
from pathlib import Path
from collections import Counter

def setup_frequency():
    """Track the conditional probability structure of V4."""
    print("="*70)
    print("  V4 SETUP FREQUENCY ANALYSIS")
    print("="*70)
    
    # Load evidence
    evidence_path = Path("research/paper/V4_CANONICAL_1.0/evidence/evaluations.jsonl")
    rows = [json.loads(x) for x in evidence_path.read_text().splitlines() if x.strip()]
    
    # Deduplicate by candle_close_time
    unique = {}
    for r in rows:
        candle = r.get('candle_close_time') or r.get('timestamp_utc')
        if candle and candle not in unique:
            unique[candle] = r
    
    candles = list(unique.values())
    n = len(candles)
    
    print(f"\n  UNIQUE H4 OBSERVATIONS: {n}")
    print(f"  (Deduplicated from {len(rows)} evidence records)")
    
    # Funnel analysis
    london = [r for r in candles if r.get('session') == 'LONDON']
    bullish = [r for r in candles if r.get('bias') == 'BULLISH']
    fvg = [r for r in candles if r.get('fvg_detected')]
    
    london_bullish = [r for r in candles if r.get('session') == 'LONDON' and r.get('bias') == 'BULLISH']
    london_fvg = [r for r in candles if r.get('session') == 'LONDON' and r.get('fvg_detected')]
    all_three = [r for r in candles if r.get('session') == 'LONDON' and r.get('bias') == 'BULLISH' and r.get('fvg_detected')]
    
    print(f"\n  CONDITIONAL FUNNEL:")
    print(f"    Total H4 observations: {n}")
    print(f"    London session:        {len(london)} ({len(london)/n*100:.1f}%)")
    print(f"    Bullish bias:          {len(bullish)} ({len(bullish)/n*100:.1f}%)")
    print(f"    FVG detected:          {len(fvg)} ({len(fvg)/n*100:.1f}%)")
    print(f"    London + Bullish:      {len(london_bullish)} ({len(london_bullish)/n*100:.1f}%)")
    print(f"    London + FVG:          {len(london_fvg)} ({len(london_fvg)/n*100:.1f}%)")
    print(f"    ALL THREE:             {len(all_three)} ({len(all_three)/n*100:.1f}%)")
    
    # Historical comparison
    print(f"\n  HISTORICAL EXPECTATION (8 years):")
    print(f"    FVG rate: 12.0%")
    print(f"    Bullish bias: 63.6%")
    print(f"    London: 16.1%")
    print(f"    Estimated valid: 12% x 63.6% x 16.1% = 1.2%")
    
    # The bottleneck
    print(f"\n  BOTTLENECK ANALYSIS:")
    if len(bullish) == 0:
        print(f"    [CRITICAL] Bullish bias = 0%")
        print(f"    This is the PRIMARY bottleneck")
    elif len(london) == 0:
        print(f"    [CRITICAL] London session = 0%")
    elif len(fvg) == 0:
        print(f"    [CRITICAL] FVG = 0%")
    else:
        print(f"    [OK] All conditions have non-zero rates")

if __name__ == "__main__":
    setup_frequency()

