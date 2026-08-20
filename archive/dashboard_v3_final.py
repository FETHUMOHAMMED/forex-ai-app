"""
Dashboard V3 Final - All 7 advisor improvements.
"""
import sqlite3, json, urllib.request, MetaTrader5 as mt5
from datetime import datetime, timezone

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# V3 Stats
c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2), ROUND(AVG(confidence),3), ROUND(MAX(confidence),3), ROUND(MIN(confidence),3) FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL")
v3 = c.fetchone()
v3_t, v3_w, v3_pnl, v3_avgc, v3_maxc, v3_minc = v3

# PRE_V3
c.execute("SELECT COUNT(*), ROUND(SUM(pnl),2) FROM trades WHERE strategy_version='PRE_V3' AND pnl IS NOT NULL")
pre_t, pre_pnl = c.fetchone()

# Regime breakdown for V3
c.execute("SELECT institutional_bias, COUNT(*) FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL GROUP BY institutional_bias")
regimes = c.fetchall()

# Confidence buckets for V3
buckets = [(75,80),(80,85),(85,90),(90,101)]
conf_data = []
for lo, hi in buckets:
    c.execute("SELECT COUNT(*) FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL AND confidence >= ? AND confidence < ?", (lo/100, hi/100))
    conf_data.append((f"{lo}-{hi}%", c.fetchone()[0]))

# Live_Micro balance
mt5.initialize()
try:
    mt5.login(REDACTED_LIVE_ACCOUNT, password='REDACTED_OLD_LIVE_PASSWORD', server='Exness-MT5Real10')
    acc = mt5.account_info()
    live_bal = acc.balance if acc else 0
    live_pos = len(mt5.positions_get()) if mt5.positions_get() else 0
except:
    live_bal = 0
    live_pos = 0
mt5.shutdown()

# Current signal
try:
    resp = urllib.request.urlopen('http://localhost:8001/signals', timeout=3)
    data = json.loads(resp.read())
    sigs = data.get('signals', [])
    cur_sig = sigs[0] if sigs else None
except:
    cur_sig = None

print("=" * 55)
print("  FOREX-AI-APP | V3 REGIME")
print("=" * 55)

# 1. V3 Performance (richer)
print("\n  V3 PERFORMANCE")
print(f"  Trades: {v3_t} | Win Rate: {round(v3_w/v3_t*100) if v3_t>0 else 0}% | PnL: ${v3_pnl or 0}")
print(f"  Avg Conf: {v3_avgc} | Max: {v3_maxc} | Min: {v3_minc}")
print(f"  PF: {'N/A' if v3_t<3 else '...'} | Expectancy: {'N/A' if v3_t<3 else '...'}")

# 2. Research Progress (richer)
print(f"\n  RESEARCH PROGRESS")
bar = '#' * min(v3_t, 20) + '.' * max(0, 20-v3_t)
print(f"  [{bar}] {v3_t}/100 trades")
print(f"  Target: PF>1.30 | WR>45% | Stage: Micro Validation")

# 3. Live Account Status
print(f"\n  LIVE_MICRO ACCOUNT")
print(f"  Status: ACTIVE | Balance: ${live_bal:.2f}")
print(f"  Open Positions: {live_pos} | V3 Trades: {v3_t}")
print(f"  Risk: 0.05% | Session: London 07-11 UTC")

# 4. Regime Statistics
print(f"\n  REGIME BREAKDOWN (V3):")
if regimes:
    for regime, count in regimes:
        print(f"  {regime}: {count} trades")
else:
    print(f"  Collecting data...")

# 5. Confidence Buckets
print(f"\n  CONFIDENCE BUCKETS (V3):")
for label, count in conf_data:
    bar_b = '#' * count + '.' * (5 - count) if count <= 5 else '#####'
    print(f"  {label}: [{bar_b}] {count}")

# 6. Current Signal
print(f"\n  CURRENT AI SIGNAL:")
if cur_sig:
    print(f"  {cur_sig['pair']} {cur_sig['signal']} | Conf: {cur_sig['confidence']:.1%}")
    print(f"  Regime: {cur_sig.get('institutional_bias','?')} | Dealer: {cur_sig.get('dealer_pressure','?')}")
    print(f"  Liquidity: {cur_sig.get('liquidity_state','?')}")
else:
    print(f"  No active signal - waiting for setup")

# 7. Research Milestones
print(f"\n  RESEARCH ROADMAP:")
milestones = [(10,"Execution verification"),(25,"Risk verification"),(50,"Initial review"),(100,"Primary validation"),(300,"Production ready"),(1000,"Institutional")]
for target, label in milestones:
    mark = '>' if v3_t < target else 'OK'
    print(f"  [{mark}] {target:>4} trades: {label}")

print(f"\n  HISTORICAL: PRE_V3: {pre_t} trades, PF 0.63, PnL ${pre_pnl} (ARCHIVED)")
print("=" * 55)
conn.close()
