"""
Walk‑forward diagnostic – relaxed filters + trade counter.
"""
import json
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
from features import FEATURE_COLUMNS
from evolve_regime_params import (
    build_regime_maps,
    fitness_vectorized,
    PAIRS, INITIAL_CAPITAL,
    SPREAD_JPY, SPREAD_NON_JPY
)
from real_ai_service import RealAITrader

# Load evolved regime parameters
with open('config.json') as f:
    config = json.load(f)
regime_params = None
for acc in config['accounts']:
    if acc['name'] == 'Live':
        regime_params = acc['regime_params']
        break
if regime_params is None:
    raise RuntimeError("No 'Live' account with regime_params in config.json")

# Relax trade minimum
import evolve_regime_params
evolve_regime_params.MIN_TRADES_REQUIRED = 10

# ---------- Temporarily disable extra filters for diagnosis ----------
evolve_regime_params.COOLDOWN_BARS = 0
evolve_regime_params.SESSION_START = 0
evolve_regime_params.SESSION_END = 23
# Also bypass spread filter by setting spread_pct to zero in the cache
# (we'll do that in the data preparation)

if not mt5.initialize():
    raise RuntimeError("MT5 not running")

# ------ 1. Fetch 2023‑2025 hourly data ------
print("📥 Fetching 2023‑2025 hourly data from MT5...")
ai = RealAITrader()
cached = {}

FEATURE_COLS = FEATURE_COLUMNS

for pair in PAIRS:
    symbol = None
    for suffix in ['', 'm', '.', 'pro']:
        if mt5.symbol_select(pair + suffix, True):
            symbol = pair + suffix
            break
    if not symbol:
        print(f"❌ {pair} not found")
        continue
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1,
                                 pd.to_datetime('2023-01-01'),
                                 pd.to_datetime('2025-01-01'))
    if rates is None or len(rates) < 100:
        continue
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df = df[['open','high','low','close','tick_volume']]
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)

    df = ai.add_indicators(df)
    if df is None or len(df) < 100:
        continue

    # Spread (percent) – set to zero to disable spread filter
    df['spread_pct'] = 0.0

    # H4 EMA distance
    h4 = df['close'].resample('4h').last()
    h4_ema200 = h4.ewm(span=200).mean()
    df['h4_ema200'] = h4_ema200.reindex(df.index, method='ffill')
    df['dist_from_h4_ema'] = (df['close'] - df['h4_ema200']) / df['h4_ema200'] * 100

    hours = df.index.hour
    df['london'] = ((hours >= 7) & (hours < 12)).astype(int)
    df['newyork'] = ((hours >= 13) & (hours < 18)).astype(int)

    atr_long = df['atr'].rolling(200).median()
    df['vol_high'] = (df['atr'] > atr_long * 1.5).astype(int)

    model = ai.models.get(pair)
    if model:
        X = df[FEATURE_COLS].fillna(0).values
        preds = model.predict(X)
        probs = model.predict_proba(X)
    else:
        preds = np.zeros(len(df), dtype=int)
        probs = np.ones((len(df), 2)) * 0.5
    df['ml_signal'] = preds
    df['ml_conf'] = np.where(preds == 1, probs[:, 1], probs[:, 0])

    df['h4_uptrend'] = df['close'] > df['h4_ema200']
    df['h4_downtrend'] = df['close'] < df['h4_ema200']
    df[['h4_uptrend','h4_downtrend']] = df[['h4_uptrend','h4_downtrend']].fillna(False)

    df = df.dropna()
    cached[pair] = df
    print(f"✅ {pair}: {len(df)} bars")

# ------ 2. Regime maps ------
regime_maps = build_regime_maps()
for pair, df in cached.items():
    if pair not in regime_maps:
        continue
    hour_index = df.index.floor('h')
    df['regime'] = hour_index.map(regime_maps[pair]).fillna('volatile')

# ------ 3. 6‑month windows ------
windows = [
    ('2023-01-01', '2023-07-01'),
    ('2023-07-01', '2024-01-01'),
    ('2024-01-01', '2024-07-01'),
    ('2024-07-01', '2025-01-01'),
]

# ------ 4. Trade counter function ------
def count_trades_vectorized(genes, cached_reg, regime_name):
    total = 0
    for pair, df in cached_reg.items():
        close = df['close'].values
        atr = df['atr'].values
        ml_sig = df['ml_signal'].values
        ml_conf = df['ml_conf'].values
        h4_up = df['h4_uptrend'].values.astype(bool)
        h4_down = df['h4_downtrend'].values.astype(bool)
        ict_buy = (df['fvg_buy'] | df['ob_buy'] | df['bb_buy'] |
                   df['lv_buy'] | df['mss_buy']).values.astype(bool)
        ict_sell = (df['fvg_sell'] | df['ob_sell'] | df['bb_sell'] |
                    df['lv_sell'] | df['mss_sell']).values.astype(bool)

        if 'JPY' in pair:
            atr_ok = (atr >= genes['atr_min_jpy']) & (atr <= genes['atr_max_jpy'])
        else:
            atr_ok = (atr >= genes['atr_min_non_jpy']) & (atr <= genes['atr_max_non_jpy'])

        if regime_name == 'trending':
            buy_sig = atr_ok & ict_buy & (ml_sig==1) & (ml_conf>=genes['min_confidence']) & h4_up
            sell_sig = atr_ok & ict_sell & (ml_sig==0) & (ml_conf>=genes['min_confidence']) & h4_down
        else:
            buy_sig = atr_ok & ict_buy & (ml_sig==1) & (ml_conf>=genes['min_confidence'])
            sell_sig = atr_ok & ict_sell & (ml_sig==0) & (ml_conf>=genes['min_confidence'])
        total += (buy_sig | sell_sig).sum()
    return total

# ------ 5. Walk‑forward ------
for regime in ['trending', 'ranging', 'volatile']:
    if isinstance(regime_params, dict) and 'global' in regime_params:
        genes = regime_params['global'][regime]
    else:
        genes = regime_params[regime]
    if genes is None:
        continue
    print(f"\n{'='*30} {regime.upper()} {'='*30}")
    scores = []
    for start, end in windows:
        regime_cache = {}
        for pair, df in cached.items():
            mask = (df.index >= pd.Timestamp(start)) & (df.index < pd.Timestamp(end))
            window_df = df[mask]
            regime_df = window_df[window_df['regime'] == regime]
            if len(regime_df) >= 500:
                regime_cache[pair] = regime_df
        if len(regime_cache) < 4:
            print(f"  {start} → {end}: skipped (need ≥4 pairs, got {len(regime_cache)})")
            continue
        score = fitness_vectorized(genes, regime_cache, regime_name=regime)
        n_trades = count_trades_vectorized(genes, regime_cache, regime_name=regime)
        scores.append(score)
        print(f"  {start} → {end}: score={score:.4f}, trades={n_trades}")

    if scores:
        avg = np.mean(scores)
        verdict = "✅ Robust" if avg > 0.3 else "⚠️ Check"
        print(f"  Average OOS: {avg:.4f}   {verdict}")
    else:
        print(f"  ❌ No valid windows processed.")