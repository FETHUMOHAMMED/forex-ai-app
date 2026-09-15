"""EXPERIMENT STATUS - Definitive count with metadata."""
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

def experiment_status():
    """Report complete experiment status with all metadata."""
    print("="*70)
    print("  V4 EXPERIMENT STATUS REPORT")
    print(f"  Generated: {datetime.now().isoformat()}")
    print("="*70)
    
    # Metadata
    print(f"\n  EXPERIMENT METADATA:")
    print(f"    Start date: 2026-08-24")
    print(f"    Symbol: USDJPYm")
    print(f"    Timeframe: H4")
    print(f"    Timezone: UTC")
    print(f"    Strategy: V4_CANONICAL_1.0")
    print(f"    Mode: PAPER")
    
    # Signal log
    signal_path = Path("research/paper/V4_CANONICAL_1.0/signal_log.jsonl")
    if signal_path.exists():
        signal_lines = signal_path.read_text().splitlines()
        signal_entries = [json.loads(x) for x in signal_lines if x.strip()]
        
        print(f"\n  SIGNAL LOG:")
        print(f"    File: {signal_path}")
        print(f"    Total entries: {len(signal_entries)}")
        if signal_entries:
            print(f"    First: {signal_entries[0].get('timestamp_utc', 'N/A')[:19]}")
            print(f"    Last: {signal_entries[-1].get('timestamp_utc', 'N/A')[:19]}")
            
            # Count by reason
            reasons = Counter(e.get('reason', 'UNKNOWN') for e in signal_entries)
            print(f"    Rejection breakdown:")
            for reason, count in reasons.most_common():
                print(f"      {reason}: {count}")
    
    # Evidence file
    evidence_path = Path("research/paper/V4_CANONICAL_1.0/evidence/evaluations.jsonl")
    if evidence_path.exists():
        evidence_lines = evidence_path.read_text().splitlines()
        evidence_entries = [json.loads(x) for x in evidence_lines if x.strip()]
        
        print(f"\n  EVIDENCE FILE:")
        print(f"    File: {evidence_path}")
        print(f"    Total entries: {len(evidence_entries)}")
        if evidence_entries:
            print(f"    First: {evidence_entries[0].get('timestamp_utc', 'N/A')[:19]}")
            print(f"    Last: {evidence_entries[-1].get('timestamp_utc', 'N/A')[:19]}")
    
    # Runner log
    runner_path = Path("research/paper/V4_CANONICAL_1.0/runner_log.jsonl")
    if runner_path.exists():
        runner_lines = runner_path.read_text().splitlines()
        runner_entries = [json.loads(x) for x in runner_lines if x.strip()]
        
        print(f"\n  RUNNER LOG:")
        print(f"    File: {runner_path}")
        print(f"    Total entries: {len(runner_entries)}")
        if runner_entries:
            print(f"    First: {runner_entries[0].get('timestamp_utc', 'N/A')[:19]}")
            print(f"    Last: {runner_entries[-1].get('timestamp_utc', 'N/A')[:19]}")
    
    # Persistent state
    state_path = Path("research/paper/V4_CANONICAL_1.0/runner_state.json")
    if state_path.exists():
        state = json.loads(state_path.read_text())
        print(f"\n  PERSISTENT STATE:")
        print(f"    File: {state_path}")
        print(f"    Total evaluations: {state.get('total_evaluations', 0)}")
        print(f"    Unique candles: {len(state.get('evaluated_candles', []))}")
    
    # ============================================
    # THE DEFINITIVE COUNT
    # ============================================
    print(f"\n{'='*70}")
    print("  DEFINITIVE COUNTS")
    print("="*70)
    
    if signal_path.exists() and evidence_path.exists():
        print(f"    Signal log entries: {len(signal_entries)}")
        print(f"    Evidence file entries: {len(evidence_entries)}")
        print(f"    Difference: {abs(len(signal_entries) - len(evidence_entries))}")
        
        if len(signal_entries) > len(evidence_entries):
            print(f"\n    Signal log has MORE entries (older format)")
        elif len(evidence_entries) > len(signal_entries):
            print(f"\n    Evidence file has MORE entries")
        else:
            print(f"\n    Both files are IN SYNC ?")
    
    # Analysis
    print(f"\n{'='*70}")
    print("  WHY THE COUNT DIFFERS")
    print("="*70)
    print(f"""
    The signal_log and evidence file have different entry counts because:
    
    1. Older runner versions wrote ONLY to signal_log
    2. Newer runner versions write to BOTH files
    3. When we killed and restarted the runner (multiple times),
       some evaluations landed only in signal_log
    
    THE EVIDENCE FILE IS THE AUTHORITATIVE SOURCE because:
    - It contains COMPLETE records (all fields)
    - It was written by the FINAL runner version
    - It uses persistent state (no resets)
    
    For statistical analysis, use: EVIDENCE FILE COUNT
    """)
    
    return len(evidence_entries) if evidence_path.exists() else 0

if __name__ == "__main__":
    experiment_status()
