"""
Filter Optimizer - Finds the best threshold combination for V2 pipeline.
Tests institutional score, ML confidence, pairs, and dealer filters.
"""
import sys, os, MetaTrader5 as mt5, pandas as pd
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '.')

from core.signal_pipeline_v2 import SignalPipelineV2
from ml.inference import predictor as ml_predictor

pipeline = SignalPipelineV2()
mt5.initialize()

# Collect all signals first
pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
all_signals = []

for pair in pairs:
    symbol = pair + 'm'
    mt5.symbol_select(symbol, True)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=90)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start, end)
    
    if rates is None or len(rates) < 200:
        continue
    
    df = pd.DataFrame(rates)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    
    for i in range(200, len(df)-20, 10):
        window = df.iloc[i-200:i].copy()
        window['time'] = pd.to_datetime(window['time'], unit='s')
        window.set_index('time', inplace=True)
        current = float(df['close'].iloc[i])
        future = float(df['close'].iloc[min(i+20, len(df)-1)])
        
        try:
            ml_sig, ml_conf = ml_predictor.predict(pair, window)
            ict_buy = current > float(window['high'].iloc[-10:].max()) * 0.998
            ict_sell = current < float(window['low'].iloc[-10:].min()) * 1.002
            sig = pipeline.generate(pair, window, ml_sig, ml_conf, ict_buy, ict_sell)
            
            if sig.is_valid:
                pnl = (future - current) / current * 10000 if sig.direction == 'BUY' else (current - future) / current * 10000
                all_signals.append({
                    'pair': pair, 'direction': sig.direction,
                    'ml_conf': sig.confidence, 'inst_score': sig.institutional_score,
                    'dealer': sig.dealer_pressure,
                    'pnl': pnl, 'win': pnl > 0
                })
        except:
            continue

mt5.shutdown()

print(f"Total signals collected: {len(all_signals)}")
print(f"\n{'='*65}")
print(f"  FILTER OPTIMIZATION RESULTS")
print(f"{'='*65}")

# Test different configurations
configs = []

# Pair combinations
pair_sets = [
    ('ALL', ['EURUSD', 'GBPUSD', 'USDJPY']),
    ('EUR+GBP', ['EURUSD', 'GBPUSD']),
    ('EURUSD', ['EURUSD']),
]

# Institutional thresholds
inst_thresholds = [50, 55, 60, 65, 70]

# ML confidence thresholds
conf_thresholds = [0.50, 0.55, 0.60, 0.65, 0.70]

# Dealer filters
dealer_filters = [
    ('ALL', None),
    ('NO_NEUTRAL', ['BUYING_PRESSURE', 'SELLING_PRESSURE', 'ACCUMULATING', 'DISTRIBUTING']),
    ('PRESSURE_ONLY', ['BUYING_PRESSURE', 'SELLING_PRESSURE']),
]

best = None
tested = 0

for pair_name, pair_list in pair_sets:
    for inst_thresh in inst_thresholds:
        for conf_thresh in conf_thresholds:
            for dealer_name, dealer_list in dealer_filters:
                tested += 1
                
                # Filter signals
                filtered = [s for s in all_signals 
                           if s['pair'] in pair_list
                           and s['inst_score'] >= inst_thresh
                           and s['ml_conf'] >= conf_thresh]
                
                if dealer_list:
                    filtered = [s for s in filtered if s['dealer'] in dealer_list]
                
                if len(filtered) < 30:
                    continue
                
                wins = sum(1 for s in filtered if s['win'])
                wr = wins / len(filtered) * 100
                total_pnl = sum(s['pnl'] for s in filtered)
                avg_pnl = total_pnl / len(filtered)
                
                # Calculate profit factor
                gross_win = sum(s['pnl'] for s in filtered if s['pnl'] > 0)
                gross_loss = abs(sum(s['pnl'] for s in filtered if s['pnl'] < 0))
                pf = gross_win / gross_loss if gross_loss > 0 else 999
                
                configs.append({
                    'pairs': pair_name, 'inst': inst_thresh, 'conf': conf_thresh,
                    'dealer': dealer_name, 'trades': len(filtered),
                    'wr': wr, 'pf': pf, 'avg_pnl': avg_pnl, 'total_pnl': total_pnl
                })

# Sort by profit factor
configs.sort(key=lambda x: x['pf'], reverse=True)

print(f"\n  Top 10 Configurations (tested {tested}):")
print(f"  {'Pairs':<10s} {'Inst':>5s} {'Conf':>5s} {'Dealer':<15s} {'Trades':>6s} {'WR':>6s} {'PF':>6s} {'PnL':>8s}")
print(f"  {'-'*10} {'-'*5} {'-'*5} {'-'*15} {'-'*6} {'-'*6} {'-'*6} {'-'*8}")

for c in configs[:10]:
    print(f"  {c['pairs']:<10s} {c['inst']:>5d} {c['conf']:>.2f} {c['dealer']:<15s} {c['trades']:>6d} {c['wr']:>5.0f}% {c['pf']:>5.2f} {c['total_pnl']:>+7.0f}")

if configs:
    best = configs[0]
    print(f"\n  BEST CONFIGURATION:")
    print(f"  Pairs: {best['pairs']} | Inst >= {best['inst']} | Conf >= {best['conf']} | Dealer: {best['dealer']}")
    print(f"  Trades: {best['trades']} | WR: {best['wr']:.0f}% | PF: {best['pf']:.2f} | PnL: {best['total_pnl']:+.0f} pips")
