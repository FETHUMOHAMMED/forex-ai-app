"""
Volume 8 Verification Script
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("  VOLUME 8 VERIFICATION - MARKET REGIME INTELLIGENCE")
print("=" * 60)

# 1. Module check
print("\n1. MODULE")
try:
    from institutional.market_regime_engine import MarketRegimeEngine, RegimeResult
    print("[PRESENT] market_regime_engine.py")
    print("[PASS] MarketRegimeEngine imported")
    print("[PASS] RegimeResult imported")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

# 2. All 8 volumes
print("\n2. ALL 8 VOLUMES")
volumes = [
    ("Volume 1", "Market Microstructure", "institutional.market_microstructure"),
    ("Volume 2", "Liquidity Intelligence", "institutional.liquidity_intelligence"),
    ("Volume 3", "Institutional Structure", "institutional.institutional_structure"),
    ("Volume 4", "Risk Engine", "institutional.institutional_risk_engine"),
    ("Volume 5", "Decision Engine", "institutional.trade_decision_engine"),
    ("Volume 6", "Learning Engine", "institutional.institutional_learning_engine"),
    ("Volume 7", "Performance Intelligence", "institutional.performance_intelligence"),
    ("Volume 8", "Market Regime Intelligence", "institutional.market_regime_engine"),
]

all_ok = True
for name, desc, module in volumes:
    try:
        __import__(module)
        print(f"[OK] {name} - {desc}")
    except Exception as e:
        print(f"[FAIL] {name} - {e}")
        all_ok = False

# 3. Database
print("\n3. DATABASE")
try:
    import sqlite3
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='regime_memory'")
    if c.fetchone():
        c.execute("PRAGMA table_info(regime_memory)")
        cols = c.fetchall()
        print(f"[PRESENT] regime_memory ({len(cols)} columns)")
    else:
        print("[MISSING] regime_memory table not found")
        all_ok = False
    conn.close()
except Exception as e:
    print(f"[FAIL] {e}")
    all_ok = False

# 4. Pipeline test
print("\n4. PIPELINE")
try:
    engine = MarketRegimeEngine()
    print("[PASS] Regime engine initialized")

    import MetaTrader5 as mt5
    import pandas as pd
    mt5.initialize()
    mt5.symbol_select('USDJPYm', True)
    rates = mt5.copy_rates_from_pos('USDJPYm', mt5.TIMEFRAME_M15, 0, 200)
    df = pd.DataFrame(rates)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    result = engine.analyze('USDJPY', df)
    print(f"[PASS] Regime analysis complete: {result.regime}")
    print(f"[PASS] Confidence: {result.regime_confidence:.0f}%")
    print(f"[PASS] Buy suitable: {result.buy_suitable}, Sell suitable: {result.sell_suitable}")

    suitable, reason = engine.is_trade_suitable(result, 'BUY')
    print(f"[PASS] Trade check: BUY={'OK' if suitable else 'NO'} - {reason}")

    mt5.shutdown()
except Exception as e:
    print(f"[FAIL] {e}")
    all_ok = False

# 5. System status
print("\n5. SYSTEM")
if all_ok:
    print("Institutional AI: READY")
    print(f"\nAll 8 volumes operational.")
else:
    print("Institutional AI: NEEDS FIX")

print("\n" + "=" * 60)
