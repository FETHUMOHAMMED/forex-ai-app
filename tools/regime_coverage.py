"""REGIME COVERAGE - Track which regimes have been observed."""
import json
from pathlib import Path
from collections import Counter

def track_coverage():
    """Track regime coverage."""
    print("="*70)
    print("  REGIME COVERAGE TRACKER")
    print("="*70)
    
    # Load data
    p = Path("research/paper/V4_CANONICAL_1.0/evidence/evaluations.jsonl")
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    
    # Deduplicate
    unique = {}
    for r in rows:
        candle = r.get('candle_close_time') or r.get('timestamp_utc')
        if candle:
            unique[candle] = r
    candles = list(unique.values())
    
    # Classify regimes
    regimes = []
    for c in candles:
        bias = c.get('bias', 'UNKNOWN')
        gap = c.get('ema_50', 0) - c.get('ema_200', 0) if 'ema_50' in c else c.get('ema_fast', 0) - c.get('ema_slow', 0)
        
        if bias == 'BEARISH':
            if gap < -1.0:
                regime = 'BEARISH_STRONG'
            elif gap < -0.3:
                regime = 'BEARISH_MODERATE'
            else:
                regime = 'BEARISH_WEAK'
        elif bias == 'BULLISH':
            if gap > 0.5:
                regime = 'BULLISH_STRONG'
            else:
                regime = 'BULLISH_WEAK'
        else:
            regime = 'UNKNOWN'
        
        regimes.append(regime)
    
    counts = Counter(regimes)
    total = len(regimes)
    
    print(f"\n  OBSERVED REGIMES ({total} candles):")
    for regime in ['BEARISH_STRONG', 'BEARISH_MODERATE', 'BEARISH_WEAK',
                   'TRANSITION', 'BULLISH_WEAK', 'BULLISH_STRONG']:
        count = counts.get(regime, 0)
        pct = count / total * 100 if total > 0 else 0
        status = '?' if count > 0 else '?'
        print(f"    {status} {regime:<20} {count:>4} ({pct:>5.1f}%)")
    
    # Coverage
    regimes_needed = ['BEARISH', 'TRANSITION', 'BULLISH']
    regimes_seen = []
    if counts.get('BEARISH_STRONG', 0) + counts.get('BEARISH_WEAK', 0) > 0:
        regimes_seen.append('BEARISH')
    if counts.get('BULLISH_STRONG', 0) + counts.get('BULLISH_WEAK', 0) > 0:
        regimes_seen.append('BULLISH')
    
    print(f"\n  COVERAGE:")
    print(f"    Bearish: {'?' if 'BEARISH' in regimes_seen else '?'}")
    print(f"    Transition: ? (detected by change)")
    print(f"    Bullish: {'?' if 'BULLISH' in regimes_seen else '?'}")
    print(f"    Coverage: {len(regimes_seen)}/3 required")

if __name__ == "__main__":
    track_coverage()



