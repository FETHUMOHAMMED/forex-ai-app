"""
Backtest V2 - Validates new pipeline against historical data.
"""
import sys, os, MetaTrader5 as mt5, pandas as pd
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '.')

from core.signal_pipeline_v2 import SignalPipelineV2
from ml.inference import predictor as ml_predictor

pipeline = SignalPipelineV2()
mt5.initialize()

pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
results = []

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
                # Simulate outcome
                if sig.direction == 'BUY':
                    pnl = (future - current) / current * 10000
                    win = future > current
                else:
                    pnl = (current - future) / current * 10000
                    win = future < current
                
                results.append({
                    'pair': pair, 'direction': sig.direction,
                    'ml_conf': sig.confidence, 'inst_score': sig.institutional_score,
                    'dealer': sig.dealer_pressure, 'liquidity': sig.liquidity_state,
                    'structure': sig.institutional_bias,
                    'pnl': round(pnl, 1), 'win': win
                })
        except:
            continue

mt5.shutdown()

# Print results
if results:
    wins = sum(1 for r in results if r['win'])
    total = len(results)
    wr = wins/total*100
    
    print(f"\n{'='*55}")
    print(f"  BACKTEST V2 - {total} trades")
    print(f"{'='*55}")
    print(f"  Win Rate: {wr:.1f}% ({wins}/{total})")
    print(f"  Avg PnL: {sum(r['pnl'] for r in results)/total:+.1f} pips")
    
    print(f"\n  By Pair:")
    for pair in pairs:
        pr = [r for r in results if r['pair']==pair]
        if pr:
            pw = sum(1 for r in pr if r['win'])
            print(f"  {pair}: {len(pr)} trades, {pw/len(pr)*100:.0f}% WR, {sum(r['pnl'] for r in pr):+.0f} pips")
    
    print(f"\n  By Structure:")
    for s in ['TRENDING_BEAR', 'TRENDING_BULL', 'BREAKOUT', 'RANGE']:
        sr = [r for r in results if r['structure']==s]
        if sr:
            sw = sum(1 for r in sr if r['win'])
            print(f"  {s}: {len(sr)} trades, {sw/len(sr)*100:.0f}% WR")
    
    print(f"\n  By Dealer:")
    for d in ['SELLING_PRESSURE', 'BUYING_PRESSURE', 'DISTRIBUTING', 'ACCUMULATING', 'NEUTRAL']:
        dr = [r for r in results if r['dealer']==d]
        if dr:
            dw = sum(1 for r in dr if r['win'])
            print(f"  {d}: {len(dr)} trades, {dw/len(dr)*100:.0f}% WR")
else:
    print("No trades generated - filters may be too strict")
