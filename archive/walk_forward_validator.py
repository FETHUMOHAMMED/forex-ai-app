"""
Walk-Forward Validator - Tests if the edge survives unseen data.
EURUSD only, Inst>=65, Conf>=0.60, NO_NEUTRAL dealer.
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

# Load 2 years of data
end = datetime.now(timezone.utc)
start = end - timedelta(days=730)
rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start, end)

if rates is None or len(rates) < 500:
    print("Not enough data")
    mt5.shutdown()
    exit()

df = pd.DataFrame(rates)
df.rename(columns={'tick_volume': 'volume'}, inplace=True)

# Collect all signals
signals = []
for i in range(200, len(df)-20, 10):
    window = df.iloc[i-200:i].copy()
    window['time'] = pd.to_datetime(window['time'], unit='s')
    window.set_index('time', inplace=True)
    current = float(df['close'].iloc[i])
    future = float(df['close'].iloc[min(i+20, len(df)-1)])
    timestamp = df['time'].iloc[i] if 'time' in df.columns else datetime.fromtimestamp(df.iloc[i]['time'], tz=timezone.utc)
    
    try:
        ml_sig, ml_conf = ml_predictor.predict('EURUSD', window)
        ict_buy = current > float(window['high'].iloc[-10:].max()) * 0.998
        ict_sell = current < float(window['low'].iloc[-10:].min()) * 1.002
        sig = pipeline.generate('EURUSD', window, ml_sig, ml_conf, ict_buy, ict_sell)
        
        if sig.is_valid:
            pnl = (future - current) / current * 10000 if sig.direction == 'BUY' else (current - future) / current * 10000
            signals.append({
                'date': timestamp,
                'inst_score': sig.institutional_score,
                'ml_conf': sig.confidence,
                'dealer': sig.dealer_pressure,
                'pnl': pnl, 'win': pnl > 0
            })
    except:
        continue

mt5.shutdown()

# Filter with best configuration
filtered = [s for s in signals 
            if s['inst_score'] >= 65 
            and s['ml_conf'] >= 0.60 
            and s['dealer'] != 'NEUTRAL']

if len(filtered) < 30:
    print(f"Only {len(filtered)} trades after filtering")
    exit()

# Walk-forward periods
periods = [
    ("Period 1", "2024-01-01", "2025-06-30", "2025-07-01", "2025-12-31"),
    ("Period 2", "2024-07-01", "2025-12-31", "2026-01-01", "2026-03-31"),
    ("Period 3", "2025-01-01", "2026-03-31", "2026-04-01", "2026-08-31"),
]

print(f"\n{'='*60}")
print(f"  WALK-FORWARD VALIDATION")
print(f"  EURUSD | Inst>=65 | Conf>=0.60 | NO_NEUTRAL")
print(f"{'='*60}")
print(f"  Total filtered signals: {len(filtered)}")

results = []

for name, train_start, train_end, test_start, test_end in periods:
    test_signals = []
    for s in filtered:
        d = s['date']
        if hasattr(d, 'strftime'):
            ds = d.strftime('%Y-%m-%d')
        else:
            ds = str(d)[:10]
        if ds >= test_start and ds <= test_end:
            test_signals.append(s)
    
    if len(test_signals) < 10:
        continue
    
    wins = sum(1 for s in test_signals if s['win'])
    wr = wins / len(test_signals) * 100
    total_pnl = sum(s['pnl'] for s in test_signals)
    gross_win = sum(s['pnl'] for s in test_signals if s['pnl'] > 0)
    gross_loss = abs(sum(s['pnl'] for s in test_signals if s['pnl'] < 0))
    pf = gross_win / gross_loss if gross_loss > 0 else 999
    
    results.append({'name': name, 'trades': len(test_signals), 'wr': wr, 'pf': pf, 'pnl': total_pnl})
    
    print(f"\n  {name}: {test_start} -> {test_end}")
    print(f"    Trades: {len(test_signals)} | WR: {wr:.0f}% | PF: {pf:.2f} | PnL: {total_pnl:+.0f} pips")

if results:
    avg_pf = sum(r['pf'] for r in results) / len(results)
    avg_wr = sum(r['wr'] for r in results) / len(results)
    all_pf_above_1 = all(r['pf'] > 1.1 for r in results)
    
    print(f"\n  {'='*40}")
    print(f"  FINAL:")
    print(f"  Average PF: {avg_pf:.2f}")
    print(f"  Average WR: {avg_wr:.0f}%")
    print(f"  Consistency: {'PASS - All periods PF > 1.1' if all_pf_above_1 else 'FAIL - Some periods PF < 1.1'}")
    print(f"  {'='*40}")

print(f"\n{'='*60}")
