"""
Verify Regime Strategy V3 - Production gatekeeper test.
"""
import sys, os, MetaTrader5 as mt5, pandas as pd
sys.path.insert(0, '.')

from core.signal_pipeline_v2 import SignalPipelineV2
from core.regime_strategy import strategy
from ml.inference import predictor as ml_predictor

print("=" * 55)
print("  REGIME STRATEGY V3 VERIFICATION")
print("=" * 55)

# 1. Unit tests
print("\n1. UNIT TESTS")
from shared.trade_signal import TradeSignal

tests = [
    ("EURUSD BREAKOUT DISTRIBUTING", True, 
     TradeSignal(pair='EURUSD', direction='SELL', confidence=0.62, entry=1.1, stop_loss=1.103, take_profit=1.094, institutional_score=68, institutional_bias='BREAKOUT', dealer_pressure='DISTRIBUTING', liquidity_state='SWEEP_SELL')),
    
    ("GBPUSD blocked", False,
     TradeSignal(pair='GBPUSD', direction='SELL', confidence=0.62, entry=1.3, stop_loss=1.303, take_profit=1.294, institutional_score=68, institutional_bias='BREAKOUT', dealer_pressure='DISTRIBUTING', liquidity_state='SWEEP_SELL')),
    
    ("RANGE blocked", False,
     TradeSignal(pair='EURUSD', direction='SELL', confidence=0.62, entry=1.1, stop_loss=1.103, take_profit=1.094, institutional_score=68, institutional_bias='RANGE', dealer_pressure='DISTRIBUTING', liquidity_state='SWEEP_SELL')),
    
    ("NEUTRAL dealer blocked", False,
     TradeSignal(pair='EURUSD', direction='SELL', confidence=0.62, entry=1.1, stop_loss=1.103, take_profit=1.094, institutional_score=68, institutional_bias='BREAKOUT', dealer_pressure='NEUTRAL', liquidity_state='SWEEP_SELL')),
    
    ("Low confidence blocked", False,
     TradeSignal(pair='EURUSD', direction='SELL', confidence=0.48, entry=1.1, stop_loss=1.103, take_profit=1.094, institutional_score=68, institutional_bias='BREAKOUT', dealer_pressure='DISTRIBUTING', liquidity_state='SWEEP_SELL')),
]

all_pass = True
for name, expected, sig in tests:
    result = strategy.validate(sig)
    passed = result == expected
    if not passed: all_pass = False
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}: expected={expected} got={result}")

# 2. Live market test
print("\n2. LIVE MARKET TEST")
pipeline = SignalPipelineV2()
mt5.initialize()

for pair in ['EURUSD', 'GBPUSD']:
    symbol = pair + 'm'
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
    df = pd.DataFrame(rates)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    ml_sig, ml_conf = ml_predictor.predict(pair, df)
    ict_buy = float(df['close'].iloc[-1]) > float(df['high'].iloc[-10:].max()) * 0.998
    ict_sell = float(df['close'].iloc[-1]) < float(df['low'].iloc[-10:].min()) * 1.002
    
    sig = pipeline.generate(pair, df, ml_sig, ml_conf, ict_buy, ict_sell)
    result = strategy.validate(sig)
    
    print(f"\n  {pair}:")
    print(f"    ML: {ml_sig} conf={ml_conf:.3f} | ICT: buy={ict_buy} sell={ict_sell}")
    print(f"    Inst: {sig.institutional_score:.0f}% | Dealer: {sig.dealer_pressure} | Structure: {sig.institutional_bias}")
    print(f"    Regime filter: {'PASS - WOULD TRADE' if result else 'REJECT - ' + sig.rejection_reason}")

mt5.shutdown()

# 3. Daemon cache check
print("\n3. DAEMON CACHE")
import urllib.request, json
try:
    resp = urllib.request.urlopen('http://localhost:8001/signals', timeout=5)
    data = json.loads(resp.read())
    sigs = data.get('signals', [])
    print(f"  Signals in cache: {len(sigs)}")
    if sigs:
        for s in sigs:
            print(f"  {s['pair']} {s['signal']} conf={s['confidence']:.3f} inst={s.get('institutional_score',0):.0f}")
    else:
        print("  Cache empty - waiting for DISTRIBUTING+BREAKOUT on EURUSD")
except Exception as e:
    print(f"  Daemon offline: {e}")

print(f"\n{'='*55}")
print(f"  {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
print(f"{'='*55}")
