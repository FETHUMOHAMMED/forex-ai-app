import sys
sys.path.insert(0, '.')
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

mt5.initialize()

pairs = ['USDJPYm', 'EURUSDm', 'USDCADm', 'GBPUSDm']
print('Volume Delta across pairs and lookbacks:')
print('=' * 55)

for sym in pairs:
    mt5.symbol_select(sym, True)
    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 500)
    if rates is None:
        continue
    df = pd.DataFrame(rates)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    
    for lookback in [10, 20, 30, 50]:
        recent = df.iloc[-lookback:]
        bull = float(recent[recent['close'] > recent['open']]['volume'].sum())
        bear = float(recent[recent['close'] < recent['open']]['volume'].sum())
        total = bull + bear
        delta = (bull - bear) / total if total > 0 else 0.0
        print(f'{sym:12s} lb={lookback:2d}: delta={delta:+.4f}  bull={bull:8.0f} bear={bear:8.0f}')

print()
print('Calibration across rolling windows:')
all_deltas = []
for sym in pairs:
    mt5.symbol_select(sym, True)
    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 500)
    if rates is None:
        continue
    df = pd.DataFrame(rates)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    for i in range(30, len(df), 5):
        window = df.iloc[i-30:i]
        bull = float(window[window['close'] > window['open']]['volume'].sum())
        bear = float(window[window['close'] < window['open']]['volume'].sum())
        total = bull + bear
        if total > 0:
            all_deltas.append(abs((bull - bear) / total))

if all_deltas:
    all_deltas = np.array(all_deltas)
    print(f'  Samples: {len(all_deltas)}')
    print(f'  Mean abs delta: {all_deltas.mean():.4f}')
    print(f'  Median abs delta: {np.median(all_deltas):.4f}')
    print(f'  60th percentile: {np.percentile(all_deltas, 60):.4f}')
    print(f'  75th percentile: {np.percentile(all_deltas, 75):.4f}')
    print(f'  90th percentile: {np.percentile(all_deltas, 90):.4f}')
    print(f'  Max abs delta: {all_deltas.max():.4f}')
    print()
    print(f'  Suggested thresholds:')
    print(f'    NEUTRAL:      < {np.percentile(all_deltas, 40):.3f}')
    print(f'    ACCUMULATING:   {np.percentile(all_deltas, 40):.3f} to {np.percentile(all_deltas, 70):.3f}')
    print(f'    PRESSURE:     > {np.percentile(all_deltas, 70):.3f}')

mt5.shutdown()
