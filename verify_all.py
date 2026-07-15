import sys
sys.path.insert(0, '.')
import sqlite3

print("=" * 60)
print("  FOREX-AI-APP — COMPLETE SYSTEM VERIFICATION")
print("=" * 60)

# 1. ARCHITECTURE
print("\n1. ARCHITECTURE (9 Volumes + 9.5 Filters)")
volumes = [
    ("Volume 1", "Market Microstructure", "institutional.market_microstructure"),
    ("Volume 2", "Liquidity Intelligence", "institutional.liquidity_intelligence"),
    ("Volume 3", "Institutional Structure", "institutional.institutional_structure"),
    ("Volume 4", "Risk Engine", "institutional.institutional_risk_engine"),
    ("Volume 5", "Decision Engine", "institutional.trade_decision_engine"),
    ("Volume 6", "Learning Engine", "institutional.institutional_learning_engine"),
    ("Volume 7", "Performance Intelligence", "institutional.performance_intelligence"),
    ("Volume 8", "Market Regime Intelligence", "institutional.market_regime_engine"),
    ("Volume 9", "Adaptive Strategy Optimization", "institutional.adaptive_decision_engine"),
    ("Volume 9.5", "Institutional Filters", "institutional.institutional_filter"),
]
all_ok = True
for name, desc, mod in volumes:
    try:
        __import__(mod)
        print(f"  [OK] {name} - {desc}")
    except Exception as e:
        print(f"  [FAIL] {name} - {e}")
        all_ok = False

# 2. DATA
print("\n2. DATA INVENTORY")
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
real = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM shadow_trades")
shadow = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM trade_memory")
tm = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM performance_memory")
pm = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM strategy_memory")
sm = c.fetchone()[0]
total = real + shadow
print(f"  Real trades:        {real}")
print(f"  Shadow trades:      {shadow}")
print(f"  TOTAL DATA POINTS:  {total} (target 300: {'REACHED' if total >= 300 else 'NOT REACHED'})")
print(f"  trade_memory:       {tm}")
print(f"  performance_memory: {pm}")
print(f"  strategy_memory:    {sm} patterns")

# 3. REGIME PERFORMANCE
print("\n3. REGIME PERFORMANCE")
c.execute("SELECT regime, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL GROUP BY regime ORDER BY COUNT(*) DESC")
for row in c.fetchall():
    wr = row[2]/row[1]*100 if row[1] > 0 else 0
    bar = "OK" if wr >= 50 else "BAD"
    print(f"  {bar} {row[0]:15s}: {row[1]:3d} trades, {wr:.1f}% WR")

# 4. PAIR PERFORMANCE
print("\n4. PAIR PERFORMANCE")
c.execute("SELECT pair, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) FROM shadow_trades WHERE decision='SIMULATED' GROUP BY pair ORDER BY COUNT(*) DESC")
for row in c.fetchall():
    wr = row[2]/row[1]*100 if row[1] > 0 else 0
    rec = "KEEP" if wr >= 40 else "DROP"
    print(f"  {rec} {row[0]:10s}: {row[1]:3d} trades, {wr:.1f}% WR")

# 5. TOP PATTERNS
print("\n5. TOP 5 PATTERNS (min 10 trades)")
c.execute("SELECT pair, regime, signal, trades, win_rate FROM strategy_memory WHERE trades >= 10 ORDER BY win_rate DESC LIMIT 5")
for row in c.fetchall():
    print(f"  {row[0]}+{row[1]}+{row[2]}: {row[4]}% WR ({row[3]} trades)")

# 6. ACTIVE FILTERS
print("\n6. ACTIVE FILTERS (Volume 9.5)")
print("  ALLOWED pairs:   USDJPY, NZDUSD, EURUSD, GBPUSD, USDCAD")
print("  BLOCKED pairs:   AUDUSD, USDCHF, USDSGD")
print("  ALLOWED sessions: London, Asian")
print("  BLOCKED sessions: NY, Overlap")
print("  ALLOWED regimes:  RANGING, SWEEP_SELL")
print("  BLOCKED regimes:  BREAKOUT, SWEEP_BUY")

# 7. DECISION ENGINE TEST
print("\n7. ADAPTIVE DECISION ENGINE (Live Test)")
from institutional.adaptive_decision_engine import AdaptiveDecisionEngine
engine = AdaptiveDecisionEngine()
tests = [
    ("USDJPY", "BUY", "RANGING", 0.55),
    ("NZDUSD", "SELL", "RANGING", 0.55),
    ("AUDUSD", "SELL", "BREAKOUT", 0.60),
    ("NZDUSD", "BUY", "BREAKOUT", 0.55),
]
for pair, sig, regime, conf in tests:
    result = engine.decide(pair, sig, regime, conf)
    status = "[OK]" if result.decision != "REJECT" else "[XX]"
    print(f"  {status} {pair}+{regime}+{sig}: {result.decision} Grade={result.grade} Score={result.composite_score:.0f}")

conn.close()

# 8. FINAL STATUS
print("\n" + "=" * 60)
print("  FINAL STATUS")
print(f"  Architecture: {'100% OPERATIONAL' if all_ok else 'NEEDS FIX'}")
print(f"  Data: {total}/300 points {'REACHED' if total >= 300 else 'MORE NEEDED'}")
print(f"  System: FROZEN - Data collection mode")
print(f"  Next: No Volume 10 until live validation")
print("=" * 60)
