"""Quick time‑segmented walk‑forward for regime parameters (debug version)"""
import json
import numpy as np
import pandas as pd
from datetime import datetime
from evolve_regime_params import (
    prepare_ticks_for_ga, build_regime_maps,
    fitness_vectorized, PAIRS, INITIAL_CAPITAL
)

# Load trained parameters
with open('config.json') as f:
    config = json.load(f)
regime_params = None
for acc in config['accounts']:
    if acc['name'] == 'Live':
        regime_params = acc['regime_params']
        break

if regime_params is None:
    raise RuntimeError("No 'Live' account with regime_params in config.json")

# Prepare full tick cache
cached_all = prepare_ticks_for_ga()

# ---------- 1. Show date range ----------
print("\n📅 Data date ranges:")
for pair, df in cached_all.items():
    print(f"  {pair}: {df.index.min().strftime('%Y-%m-%d')} → {df.index.max().strftime('%Y-%m-%d')}  ({len(df)} bars)")

# ---------- 2. Define windows (make sure they fit your data) ----------
# Use pandas Timestamp for correct comparison
windows = [
    (pd.Timestamp('2024-01-01'), pd.Timestamp('2024-04-01')),
    (pd.Timestamp('2024-04-01'), pd.Timestamp('2024-07-01')),
    (pd.Timestamp('2024-07-01'), pd.Timestamp('2024-10-01')),
    (pd.Timestamp('2024-10-01'), pd.Timestamp('2025-01-01')),
]

for regime in ['trending', 'ranging', 'volatile']:
    genes = regime_params.get(regime)
    if genes is None:
        print(f"\n⚠️ Regime '{regime}' not found in config. Skipping.")
        continue

    print(f"\n--- {regime.upper()} WALK‑FORWARD ---")
    scores = []

    for start, end in windows:
        test_cache = {}
        print(f"  Testing window {start.date()} → {end.date()}")
        for pair, df in cached_all.items():
            mask = (df.index >= start) & (df.index < end)
            test_df = df[mask]
            bars = len(test_df)
            print(f"    {pair}: {bars} bars", end='')
            if bars > 1000:
                test_cache[pair] = test_df
                print(" ✅ kept")
            else:
                print(" ❌ discarded (<1000)")

        print(f"  Pairs passing filter: {len(test_cache)}")
        if len(test_cache) < 4:
            print(f"  ⚠️  Skipping window (need ≥4 pairs, got {len(test_cache)})")
            continue

        score = fitness_vectorized(genes, test_cache)
        scores.append(score)
        print(f"  ✅ Score: {score:.4f}")

    if scores:
        avg = np.mean(scores)
        verdict = "✅ Robust" if avg > 0.3 else "⚠️ Check"
        print(f"  Average OOS: {avg:.4f}   {verdict}")
    else:
        print(f"  ❌ No valid windows processed.")