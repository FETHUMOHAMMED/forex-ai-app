"""RESEARCH CHECKPOINT - Uses AUTHORITATIVE V2 baseline."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json
from pathlib import Path
from datetime import datetime, timezone

def generate_checkpoint():
    print("="*70)
    print("  2-WEEK RESEARCH CHECKPOINT (V2 AUTHORITATIVE)")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*70)
    
    # Run V2 authoritative replay
    print(f"\n  [1/2] Running AUTHORITATIVE V2 replay...")
    from packages.research.canonical_replay_v2 import CanonicalReplayV2
    replay = CanonicalReplayV2()
    historical = replay.run_replay()
    
    # Get paper runner stats
    print(f"\n  [2/2] Getting prospective paper stats...")
    signal_log = Path("research/paper/V4_CANONICAL_1.0/signal_log.jsonl")
    paper_evaluations = 0
    paper_trades = 0
    if signal_log.exists():
        with open(signal_log) as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    paper_evaluations += 1
                    if entry.get("signal") == True:
                        paper_trades += 1
    
    print(f"\n{'='*70}")
    print("  CHECKPOINT SUMMARY")
    print("="*70)
    
    print(f"\n  HISTORICAL (V2 Authoritative):")
    if historical:
        print(f"    Trades: {historical.get('trades', 0)}")
        print(f"    Win rate: {historical.get('win_rate', 0)*100:.1f}%")
        print(f"    PF: {historical.get('pf', 0):.3f}")
        print(f"    Expectancy: {historical.get('expectancy', 0):.3f}R")
        print(f"    Total R: {historical.get('total_r', 0):.1f}")
    
    print(f"\n  PROSPECTIVE (Paper):")
    print(f"    Evaluations: {paper_evaluations}")
    print(f"    Paper trades: {paper_trades}")
    print(f"    Paper rejections: {paper_evaluations - paper_trades}")
    
    print(f"\n  LIVE MICRO:")
    print(f"    Status: LOCKED")
    print(f"    Reason: Capital insufficient")
    
    print(f"\n{'='*70}")
    print("  STATUS: EXPERIMENT ACTIVE")
    print("="*70)

if __name__ == "__main__":
    generate_checkpoint()

