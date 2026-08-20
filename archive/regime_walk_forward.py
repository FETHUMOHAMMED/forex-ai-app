"""
Regime Analysis - Where does the edge exist?
Breaks down performance by regime, dealer, and market condition.
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
        
        if sig.is_valid:
            pnl = (future - current) / current * 10000 if sig.direction == 'BUY' else (current - future) / current * 10000
            signals.append({
                'dealer': sig.dealer_pressure,
                'structure': sig.institutional_bias,
                'liquidity': sig.liquidity_state,
                'conf': sig.confidence,
                'inst': sig.institutional_score,
                'pnl': pnl, 'win': pnl > 0
            })
    except:
        continue

mt5.shutdown()

print(f"Total signals: {len(signals)}")
print(f"\n{'='*55}")
print(f"  REGIME ANALYSIS - Where is the edge?")
print(f"{'='*55}")

def analyze_group(name, key, data):
    groups = {}
    for s in data:
        val = s[key]
        if val not in groups:
            groups[val] = []
        groups[val].append(s)
    
    print(f"\n  By {name}:")
    for val in sorted(groups.keys(), key=lambda v: len(groups[v]), reverse=True):
        g = groups[val]
        if len(g) < 10:
            continue
        wins = sum(1 for s in g if s['win'])
        wr = wins/len(g)*100
        total = sum(s['pnl'] for s in g)
        gross_win = sum(s['pnl'] for s in g if s['pnl'] > 0)
        gross_loss = abs(sum(s['pnl'] for s in g if s['pnl'] < 0))
        pf = gross_win/gross_loss if gross_loss > 0 else 999
        marker = "EDGE?" if pf > 1.2 else ""
        print(f"  {val:<20s}: {len(g):>5d} trades, {wr:>5.0f}% WR, PF={pf:.2f} {marker}")

analyze_group("Dealer Pressure", "dealer", signals)
analyze_group("Structure", "structure", signals)
analyze_group("Liquidity", "liquidity", signals)

# Best combination
print(f"\n  Best Combos (min 30 trades):")
combos = {}
for s in signals:
    key = f"{s['dealer']}+{s['structure']}"
    if key not in combos: combos[key] = []
    combos[key].append(s)

sorted_combos = sorted(combos.items(), key=lambda x: sum(s['pnl'] for s in x[1])/len(x[1]) if len(x[1])>=30 else -999, reverse=True)
for key, g in sorted_combos[:5]:
    if len(g) < 30: continue
    wins = sum(1 for s in g if s['win'])
    wr = wins/len(g)*100
    total = sum(s['pnl'] for s in g)
    gross_win = sum(s['pnl'] for s in g if s['pnl'] > 0)
    gross_loss = abs(sum(s['pnl'] for s in g if s['pnl'] < 0))
    pf = gross_win/gross_loss if gross_loss > 0 else 999
    print(f"  {key:<30s}: {len(g):>4d} trades, {wr:.0f}% WR, PF={pf:.2f}")

print(f"\n{'='*55}")
