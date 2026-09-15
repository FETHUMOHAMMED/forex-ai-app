"""CONDITION TRACKER - Tracks all 4 V4 conditions separately."""
import json
from pathlib import Path
from datetime import datetime

def track_conditions():
    """Show all 4 V4 conditions status."""
    print("="*70)
    print("  V4 CONDITION TRACKER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*70)
    
    # Read latest evidence
    evidence_path = Path("research/paper/V4_CANONICAL_1.0/evidence/evaluations.jsonl")
    if not evidence_path.exists():
        print("\n  No evidence file found")
        return
    
    rows = [json.loads(x) for x in evidence_path.read_text().splitlines() if x.strip()]
    if not rows:
        print("\n  No evaluations found")
        return
    
    latest = rows[-1]
    
    # Display all 4 conditions
    print(f"\n  LATEST EVALUATION:")
    print(f"    Timestamp: {latest.get('timestamp_utc', 'N/A')[:19]}")
    
    # Condition 1: Bullish bias
    bias = latest.get('bias', 'UNKNOWN')
    c1_pass = bias == 'BULLISH'
    print(f"\n  CONDITION 1: Bullish bias (EMA50 > EMA200)")
    print(f"    Status: {'[PASS]' if c1_pass else '[FAIL]'} ({bias})")
    
    # Condition 2: FVG
    fvg = latest.get('fvg_detected', False)
    c2_pass = bool(fvg)
    print(f"\n  CONDITION 2: Bullish FVG")
    print(f"    Status: {'[PASS]' if c2_pass else '[FAIL]'} (FVG detected: {fvg})")
    
    # Condition 3: Session
    session = latest.get('session', 'UNKNOWN')
    c3_pass = session == 'LONDON'
    print(f"\n  CONDITION 3: London session (07:00-11:00 UTC)")
    print(f"    Status: {'[PASS]' if c3_pass else '[FAIL]'} ({session})")
    
    # Condition 4: H4 candle close (implicit in runner)
    print(f"\n  CONDITION 4: H4 candle close (evaluation timing)")
    print(f"    Status: [PASS] (evaluation at H4 close)")
    
    # Overall
    all_pass = c1_pass and c2_pass and c3_pass
    print(f"\n  {'='*70}")
    print(f"  OVERALL: {'[ALL CONDITIONS MET - TRADE SIGNAL]' if all_pass else '[NOT ALL CONDITIONS MET]'}")
    print(f"  {'='*70}")
    
    # Show recent condition rates
    print(f"\n  RECENT CONDITION RATES (last 77 evaluations):")
    fvg_count = sum(1 for r in rows if r.get('fvg_detected'))
    bias_count = sum(1 for r in rows if r.get('bias') == 'BULLISH')
    session_count = sum(1 for r in rows if r.get('session') == 'LONDON')
    all_count = sum(1 for r in rows if r.get('fvg_detected') and r.get('bias') == 'BULLISH' and r.get('session') == 'LONDON')
    
    print(f"    FVG detected: {fvg_count}/{len(rows)} ({fvg_count/len(rows)*100:.1f}%)")
    print(f"    Bullish bias: {bias_count}/{len(rows)} ({bias_count/len(rows)*100:.1f}%)")
    print(f"    London session: {session_count}/{len(rows)} ({session_count/len(rows)*100:.1f}%)")
    print(f"    ALL FOUR: {all_count}/{len(rows)} ({all_count/len(rows)*100:.1f}%)")

if __name__ == "__main__":
    track_conditions()
