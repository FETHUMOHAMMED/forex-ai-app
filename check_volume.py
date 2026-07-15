import sys
sys.path.insert(0, '.')
import MetaTrader5 as mt5
import pandas as pd
from institutional.market_microstructure import MarketMicrostructure

mt5.initialize()
mm = MarketMicrostructure()

rates = mt5.copy_rates_from_pos('USDJPYm', mt5.TIMEFRAME_M15, 0, 500)
df = pd.DataFrame(rates)
df.rename(columns={'tick_volume': 'volume'}, inplace=True)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

vol_mean = df['volume'].mean()
vol_min = df['volume'].min()
vol_max = df['volume'].max()
vol_zeros = (df['volume'] == 0).sum()
print(f'Volume stats:')
print(f'  Mean: {vol_mean:.0f}')
print(f'  Min: {vol_min}')
print(f'  Max: {vol_max}')
print(f'  Zeros: {vol_zeros}/{len(df)}')

ms = mm.analyze('USDJPY', df)
print(f'Result:')
print(f'  bias: {ms.institutional_bias}')
print(f'  score: {ms.microstructure_score:.1f}')
print(f'  dealer_pressure: {ms.dealer_pressure}')
print(f'  volume_delta: {ms.volume_delta:.3f}')
print(f'  volume_trend: {ms.volume_trend:.3f}')
print(f'  cont_prob: {ms.continuation_probability:.3f}')

recent = df.iloc[-30:]
bull_vol = recent[recent['close'] > recent['open']]['volume'].sum()
bear_vol = recent[recent['close'] < recent['open']]['volume'].sum()
total_v = bull_vol + bear_vol
delta_val = (bull_vol - bear_vol) / total_v if total_v > 0 else 0
print(f'Manual check:')
print(f'  Bull vol: {bull_vol}')
print(f'  Bear vol: {bear_vol}')
print(f'  Delta: {delta_val:.3f}')

mt5.shutdown()
