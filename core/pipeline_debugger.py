"""
Pipeline Debugger - Shows exactly where each signal gets rejected.
"""
import sys, os, MetaTrader5 as mt5, pandas as pd
sys.path.insert(0, '.')

from core.signal_pipeline import SignalPipeline
from ml.inference import predictor as ml_predictor

pipeline = SignalPipeline()
mt5.initialize()

pairs = ['EURUSD', 'GBPUSD']

for pair in pairs:
    print(f"\n{'='*50}")
    print(f"  {pair} PIPELINE TRACE")
    print(f"{'='*50}")
    
    symbol = pair + 'm'
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
    
    if rates is None:
        print("  [FAIL] No MT5 data")
        continue
    
    df = pd.DataFrame(rates)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    print("  [PASS] Market data: 200 bars")
    
    # ML prediction
    ml_signal, ml_conf = ml_predictor.predict(pair, df)
    if ml_signal:
        print(f"  [PASS] ML: {ml_signal} conf={ml_conf:.3f}")
    else:
        print(f"  [FAIL] ML: No prediction")
    
    # ICT (simplified)
    ict_buy = float(df['close'].iloc[-1]) > float(df['high'].iloc[-10:].max()) * 0.998
    ict_sell = float(df['close'].iloc[-1]) < float(df['low'].iloc[-10:].min()) * 1.002
    print(f"  [{'PASS' if ict_buy or ict_sell else 'FAIL'}] ICT: buy={ict_buy} sell={ict_sell}")
    
    # Generate through pipeline
    sig = pipeline.generate(pair, df, ml_signal, ml_conf, ict_buy, ict_sell)
    
    print(f"  [{'PASS' if sig.is_valid else 'FAIL'}] Pipeline: valid={sig.is_valid}")
    if not sig.is_valid:
        print(f"  [REJECT] Reason: {sig.rejection_reason}")
    
    # Institutional details
    print(f"  Inst Score: {sig.institutional_score:.0f} | Dealer: {sig.dealer_pressure} | Liq: {sig.liquidity_state}")
    print(f"  Bias: {sig.institutional_bias} | Regime: {sig.regime}")

mt5.shutdown()
print(f"\n{'='*50}")
