"""
Walk-Forward V2 - Simple split validation without date parsing issues.
"""
import sys, os, MetaTrader5 as mt5, pandas as pd
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '.')

from core.signal_pipeline_v2 import SignalPipelineV2
from ml.inference import predictor as ml_predictor

pipeline = SignalPipelineV2()
mt5.initialize()

symbol = 'EURUSDm'
mt5.symbol_select(symbol, True)
end = datetime.now(timezone.utc)
start = end - timedelta(days=730)
rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start, end)

df = pd.DataFrame(rates)
df.rename(columns={'tick_volume': 'volume'}, inplace=True)

signals = []
for i in range(200, len(df)-20, 10):
    window = df.iloc[i-200:i].copy()
    window['time'] = pd.to_datetime(window['time'], unit='s')
    window.set_index('time', inplace=True)
    current = float(df['close'].iloc[i])
    future = float(df['close'].iloc[min(i+20, len(df)-1)])
    
    try:
        ml_sig, ml_conf = ml_predictor.predict('EURUSD', window)
        ict_buy = current > float(window['high'].iloc[-10:].max()) * 0.998
        ict_sell = current < float(window['low'].iloc[-10:].min()) * 1.002
        sig = pipeline.generate('EURUSD', window, ml_sig, ml_conf, ict_buy, ict_sell)
        if sig.is_valid and sig.institutional_score >= 65 and sig.confidence >= 0.60 and sig.dealer_pressure != 'NEUTRAL':
            pnl = (future - current) / current * 10000 if sig.direction == 'BUY' else (current - future) / current * 10000
            signals.append({'pnl': pnl, 'win': pnl > 0})
    except:
        continue

mt5.shutdown()

total = len(signals)
print(f"Total signals: {total}")

# Split into 3 equal periods
third = total // 3
periods = [
    ("Period 1", signals[:third]),
    ("Period 2", signals[third:2*third]),
    ("Period 3", signals[2*third:]),
]

print(f"\n{'='*55}")
print(f"  WALK-FORWARD VALIDATION")
print(f"  EURUSD | Inst>=65 | Conf>=0.60 | NO_NEUTRAL")
print(f"{'='*55}")

all_pf = []
for name, sigs in periods:
    if len(sigs) < 10:
        continue
    wins = sum(1 for s in sigs if s['win'])
    wr = wins / len(sigs) * 100
    total_pnl = sum(s['pnl'] for s in sigs)
    gross_win = sum(s['pnl'] for s in sigs if s['pnl'] > 0)
    gross_loss = abs(sum(s['pnl'] for s in sigs if s['pnl'] < 0))
    pf = gross_win / gross_loss if gross_loss > 0 else 999
    all_pf.append(pf)
    print(f"\n  {name}: {len(sigs)} trades | WR: {wr:.0f}% | PF: {pf:.2f} | PnL: {total_pnl:+.0f} pips")

if all_pf:
    avg_pf = sum(all_pf) / len(all_pf)
    all_ok = all(pf > 1.1 for pf in all_pf)
    print(f"\n  {'='*40}")
    print(f"  Avg PF: {avg_pf:.2f}")
    print(f"  Consistency: {'PASS' if all_ok else 'FAIL'}")
    print(f"  {'='*40}")
print(f"\n{'='*55}")
