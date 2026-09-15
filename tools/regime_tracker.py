"""REGIME TRACKER - Tracks duration and transitions of market regime."""
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

def track_regime():
    """Track the current regime and its duration."""
    print("="*70)
    print("  V4 REGIME TRACKER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*70)
    
    # Load evidence
    evidence_path = Path("research/paper/V4_CANONICAL_1.0/evidence/evaluations.jsonl")
    rows = [json.loads(x) for x in evidence_path.read_text().splitlines() if x.strip()]
    
    if not rows:
        print("\n  No data")
        return
    
    # Deduplicate by candle time
    unique = {}
    for r in rows:
        candle = r.get('candle_close_time') or r.get('timestamp_utc')
        if candle and candle not in unique:
            unique[candle] = r
    
    candles = sorted(unique.values(), key=lambda x: x.get('timestamp_utc', ''))
    
    # Classify each candle by regime
    regimes = []
    for c in candles:
        bias = c.get('bias', 'UNKNOWN')
        gap = c.get('ema_fast', 0) - c.get('ema_slow', 0) if 'ema_fast' in c else c.get('ema_50', 0) - c.get('ema_200', 0)
        regimes.append({
            'timestamp': c.get('timestamp_utc', ''),
            'bias': bias,
            'gap': gap,
            'fvg': c.get('fvg_detected', False),
            'session': c.get('session', 'UNKNOWN')
        })
    
    # Current regime analysis
    current = regimes[-1] if regimes else None
    
    if not current:
        print("  No current data")
        return
    
    print(f"\n  CURRENT REGIME:")
    print(f"    Bias: {current['bias']}")
    print(f"    EMA gap: {current['gap']:+.4f}")
    print(f"    Last candle: {current['timestamp'][:19]}")
    
    # Find bearish streak
    bearish_candles = [r for r in regimes if r['bias'] == 'BEARISH']
    bullish_candles = [r for r in regimes if r['bias'] == 'BULLISH']
    
    # Count consecutive bearish from the end
    consecutive_bearish = 0
    for r in reversed(regimes):
        if r['bias'] == 'BEARISH':
            consecutive_bearish += 1
        else:
            break
    
    # Gap statistics
    if bearish_candles:
        gaps = [r['gap'] for r in bearish_candles]
        min_gap = min(gaps)
        max_gap = max(gaps)  # Closest to zero
        avg_gap = sum(gaps) / len(gaps)
        
        print(f"\n  BEARISH REGIME STATS:")
        print(f"    Total bearish observations: {len(bearish_candles)}")
        print(f"    Consecutive bearish (current streak): {consecutive_bearish}")
        print(f"    First bearish: {bearish_candles[0]['timestamp'][:19]}")
        print(f"    Most recent: {bearish_candles[-1]['timestamp'][:19]}")
        print(f"    Min gap (most negative): {min_gap:+.4f}")
        print(f"    Max gap (closest to zero): {max_gap:+.4f}")
        print(f"    Average gap: {avg_gap:+.4f}")
        print(f"    Current gap: {current['gap']:+.4f}")
        
        # Trend of the gap
        recent_gaps = [r['gap'] for r in regimes[-10:]]
        if len(recent_gaps) >= 2:
            gap_trend = recent_gaps[-1] - recent_gaps[0]
            if gap_trend > 0:
                print(f"    Gap trend (last 10): NARROWING ({gap_trend:+.4f})")
            else:
                print(f"    Gap trend (last 10): WIDENING ({gap_trend:+.4f})")
    
    # The transition tracking
    print(f"\n  {'='*70}")
    print(f"  REGIME TRANSITION TRACKING")
    print(f"  {'='*70}")
    
    if current['bias'] == 'BEARISH':
        print(f"\n  Current state: BEARISH")
        print(f"  Waiting for transition:")
        print(f"    BEARISH")
        print(f"       ?")
        print(f"    EMA gap approaching 0 (currently {current['gap']:+.4f})")
        print(f"       ?")
        print(f"    EMA50 crosses EMA200 (gap > 0)")
        print(f"       ?")
        print(f"    BULLISH")
        print(f"       ?")
        print(f"    FVG? (need bullish FVG)")
        print(f"       ?")
        print(f"    London? (need 07:00-11:00 UTC)")
        print(f"       ?")
        print(f"    VALID V4 SETUP?")
        
        # Distance to bullish
        print(f"\n  Distance to bullish crossover:")
        print(f"    Current gap: {current['gap']:+.4f}")
        print(f"    Need: gap > 0")
        print(f"    Distance: {abs(current['gap']):.4f} points")
    
    # Timeline
    if regimes:
        first = regimes[0]
        print(f"\n  OBSERVATION TIMELINE:")
        print(f"    First candle: {first['timestamp'][:19]} ({first['bias']})")
        print(f"    Last candle: {regimes[-1]['timestamp'][:19]} ({regimes[-1]['bias']})")
        
        # Days elapsed
        try:
            first_dt = datetime.fromisoformat(first['timestamp'].replace('Z', '+00:00'))
            last_dt = datetime.fromisoformat(regimes[-1]['timestamp'].replace('Z', '+00:00'))
            days = (last_dt - first_dt).days
            print(f"    Days elapsed: {days}")
            print(f"    Total candles: {len(regimes)}")
        except:
            pass

if __name__ == "__main__":
    track_regime()
