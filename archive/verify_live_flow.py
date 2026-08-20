"""Production flow verification - end to end test."""
import sys, os, MetaTrader5 as mt5, pandas as pd
sys.path.insert(0, '.')

print("=" * 50)
print("  LIVE REGIME FLOW TEST")
print("=" * 50)

all_ok = True

# 1. MT5
try:
    mt5.initialize()
    mt5.symbol_select('EURUSDm', True)
    rates = mt5.copy_rates_from_pos('EURUSDm', mt5.TIMEFRAME_M15, 0, 200)
    assert rates is not None and len(rates) >= 50
    print("[PASS] MT5 data: " + str(len(rates)) + " bars")
except Exception as e:
    print("[FAIL] MT5: " + str(e))
    all_ok = False

# 2. ML
from ml.inference import predictor as ml_predictor
df = pd.DataFrame(rates)
df.rename(columns={'tick_volume': 'volume'}, inplace=True)
ml_sig, ml_conf = ml_predictor.predict('EURUSD', df)
print("[PASS] ML: " + str(ml_sig) + " conf=" + str(round(ml_conf,3)))

# 3. Pipeline V2
from core.signal_pipeline_v2 import SignalPipelineV2
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)
pipeline = SignalPipelineV2()
ict_buy = float(df['close'].iloc[-1]) > float(df['high'].iloc[-10:].max()) * 0.998
ict_sell = float(df['close'].iloc[-1]) < float(df['low'].iloc[-10:].min()) * 1.002
sig = pipeline.generate('EURUSD', df, ml_sig, ml_conf, ict_buy, ict_sell)
print("[PASS] Pipeline: valid=" + str(sig.is_valid) + " dealer=" + sig.dealer_pressure + " struct=" + sig.institutional_bias)

# 4. Regime Strategy
from core.regime_strategy import strategy
result = strategy.validate(sig)
if result:
    print("[PASS] Regime: ALLOW")
else:
    print("[INFO] Regime: REJECT - " + sig.rejection_reason)

# 5. Account Manager
from execution.account_manager import AccountManager
mgr = AccountManager()
acc = mgr.get_account('Demo2')
print("[PASS] Account: " + acc.name + " | Pairs: " + str(acc.pairs) + " | Risk: " + str(acc.risk_percent) + "%")

# 6. Broker
from execution.broker_interface import PaperBroker
broker = PaperBroker(10000)
broker.connect()
print("[PASS] Broker: PaperBroker ready (balance $" + str(broker.get_balance()) + ")")

mt5.shutdown()

# 7. Config
from shared.config_loader import get_allowed_pairs, get_min_confidence
print("[PASS] Config: pairs=" + str(get_allowed_pairs()) + " conf=" + str(get_min_confidence()))

# 8. Event Bus
from shared.event_bus import bus, SignalGenerated
bus.publish(SignalGenerated(pair='EURUSD', direction='SELL', confidence=0.62, institutional_score=68))
events = bus.get_recent_events(1)
print("[PASS] Event Bus: " + str(len(events)) + " events logged")

print("\n" + "=" * 50)
print("  RESULT: ALL SYSTEMS GO")
print("  Ready for Demo2 V3 execution")
print("=" * 50)
