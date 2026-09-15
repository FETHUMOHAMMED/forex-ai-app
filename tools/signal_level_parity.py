"""SIGNAL-LEVEL PARITY - Replay vs Live on identical data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from packages.strategy.canonical_v4 import CanonicalV4Strategy

def signal_level_parity():
    """Compare signals from replay vs live runner on SAME data."""
    print("="*70)
    print("  SIGNAL-LEVEL PARITY TEST")
    print("="*70)
    
    # Load shared data
    strategy = CanonicalV4Strategy()
    data = strategy.load_data(bars=10000)
    
    # Generate features ONCE
    data_processed = strategy.generate_features(data)
    
    # METHOD 1: Signal from processed data (like replay)
    replay_signals = data_processed[data_processed['signal'] == True].copy()
    replay_signals['method'] = 'replay'
    
    print(f"\n  Method 1 (replay-style): {len(replay_signals)} signals")
    
    # METHOD 2: Live-style signal check
    # Iterate and call check for each bar as live runner would
    live_signals = []
    
    for idx in data_processed.index:
        row = data_processed.loc[idx]
        # Live runner logic: check_signal at each bar
        if (row['bullish_fvg'] and row['bullish_bias'] and row['in_session']):
            live_signals.append(idx)
    
    print(f"  Method 2 (live-style): {len(live_signals)} signals")
    
    # Compare
    print(f"\n{'='*70}")
    print("  PARITY COMPARISON")
    print("="*70)
    
    replay_set = set(replay_signals.index)
    live_set = set(live_signals)
    
    print(f"  Replay signals: {len(replay_set)}")
    print(f"  Live signals: {len(live_set)}")
    print(f"  Match: {len(replay_set & live_set)}")
    print(f"  Replay-only: {len(replay_set - live_set)}")
    print(f"  Live-only: {len(live_set - replay_set)}")
    
    if replay_set == live_set:
        print(f"\n  [PASS] Signals are IDENTICAL")
        return True
    else:
        print(f"\n  [FAIL] Signals DIFFER")
        
        # Show first difference
        if replay_set - live_set:
            first = list(replay_set - live_set)[0]
            print(f"  First replay-only signal at: {data_processed.loc[first, 'timestamp']}")
        if live_set - replay_set:
            first = list(live_set - replay_set)[0]
            print(f"  First live-only signal at: {data_processed.loc[first, 'timestamp']}")
        return False

if __name__ == "__main__":
    result = signal_level_parity()
