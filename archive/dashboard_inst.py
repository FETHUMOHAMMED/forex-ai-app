# -*- coding: utf-8 -*-
"""Institutional Dashboard - Plain ASCII for compatibility"""
import sqlite3, json, urllib.request, MetaTrader5 as mt5
from datetime import datetime, timezone

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("""SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END),
             ROUND(SUM(pnl),2), ROUND(AVG(CASE WHEN pnl>0 THEN pnl END),2), 
             ROUND(AVG(CASE WHEN pnl<0 THEN pnl END),2), ROUND(AVG(confidence),3),
             ROUND(MAX(CASE WHEN pnl<0 THEN pnl END),2)
             FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL""")
v3 = c.fetchone()
t, w, l, pnl, aw, al, ac, max_dd = v3
wr = round(w/t*100,1) if t>0 else 0

gross_win = w*(aw or 0) if aw else 0
gross_loss = abs(l*(al or 0)) if al else 1
pf = round(gross_win/gross_loss,2) if gross_loss>0 else 'N/A'
ev = round((wr/100)*(aw or 0) - ((100-wr)/100)*abs(al or 0),2) if t>0 and aw and al else 'N/A'
avg_r = round((aw or 0)/abs(al or 1),2) if aw and al else 'N/A'

c.execute("SELECT COUNT(*), ROUND(SUM(pnl),2) FROM trades WHERE strategy_version='PRE_V3' AND pnl IS NOT NULL")
pre_t, pre_pnl = c.fetchone()

# Regimes
c.execute("""SELECT institutional_bias, COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2)
             FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL GROUP BY institutional_bias""")
regimes = c.fetchall()

# Confidence buckets
buckets = [(0.75,0.80),(0.80,0.85),(0.85,0.90),(0.90,1.01)]
conf_data = []
for lo, hi in buckets:
    c.execute("""SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2) 
                 FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL 
                 AND confidence>=? AND confidence<?""", (lo, hi))
    r = c.fetchone()
    conf_data.append((f"{int(lo*100)}-{int(hi*100)}%", r[0], r[1] or 0, r[2] or 0))

# Live account
mt5.initialize()
live_bal = 0; live_eq = 0; live_positions = 0; floating_pnl = 0
try:
    if mt5.login(REDACTED_LIVE_ACCOUNT, password='REDACTED_OLD_LIVE_PASSWORD', server='Exness-MT5Real10'):
        acc = mt5.account_info()
        if acc: live_bal = acc.balance; live_eq = acc.equity
        pos = mt5.positions_get()
        if pos: live_positions = len(pos); floating_pnl = sum(p.profit for p in pos)
except: pass

# Current signal
try:
    resp = urllib.request.urlopen('http://localhost:8001/signals', timeout=3)
    data = json.loads(resp.read())
    sigs = data.get('signals', [])
    cur = sigs[0] if sigs else None
except: cur = None

# RENDER
print("=" * 60)
print("  FOREX-AI-APP | INSTITUTIONAL TRADING DASHBOARD")
print(f"  V3_REGIME | LIVE MICRO | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 60)

print("\n--- PERFORMANCE METRICS (V3 ONLY) ---")
print(f"  Trades: {t} ({w}W/{l}L) | WR: {wr}% | PF: {pf} | Expectancy: ${ev}")
print(f"  Avg Win: ${aw or 'N/A'} | Avg Loss: ${al or 'N/A'} | Avg R: {avg_r}")
print(f"  Max DD: ${max_dd or 'N/A'} | Net PnL: ${pnl or 0} | Avg Conf: {ac}")

print("\n--- LIVE MICRO ACCOUNT ---")
print(f"  Balance: ${live_bal:,.2f} | Equity: ${live_eq:,.2f}")
print(f"  Positions: {live_positions} | Floating: ${floating_pnl:+,.2f}")

print("\n--- REGIME PERFORMANCE ---")
if regimes:
    for regime, rt, rw, rpnl in regimes:
        print(f"  {regime:<25s} {rt:>4d} trades  {round(rw/rt*100) if rt>0 else 0:>5}% WR  ${rpnl:>+8}")
else:
    print("  Collecting...")

print("\n--- CONFIDENCE CALIBRATION ---")
for label, ct, cw, cpnl in conf_data:
    print(f"  {label:<12s} {ct:>4d} trades  {cw:>4d} wins  ${cpnl:>+7}")

print("\n--- CURRENT AI SIGNAL ---")
if cur:
    print(f"  {cur['pair']} {cur['signal']} @ {cur['confidence']:.1%} | {cur.get('institutional_bias','?')}")
    print(f"  Dealer: {cur.get('dealer_pressure','?')} | Liq: {cur.get('liquidity_state','?')}")
    print(f"  SL: {cur.get('stop_loss',0):.5f} | TP: {cur.get('take_profit',0):.5f}")
else:
    print("  No active signal")

print("\n--- INSTITUTIONAL SCORECARD ---")
for name, score in [("Execution",5),("Risk Mgmt",5),("Data Quality",5),("Regime Detection",5),
                     ("ML Pipeline",5),("Position Mgmt",4),("Trade Logging",5),("Statistical Proof",1)]:
    stars = "*"*score + "."*(5-score)
    print(f"  {name:<25s} {stars}")

print("\n--- RESEARCH ROADMAP ---")
for target, label in [(10,"Execution Verified"),(25,"Risk Verified"),(50,"Initial Review"),
                       (100,"Statistical Validity"),(300,"Production Ready"),(1000,"Institutional Grade")]:
    print(f"  [{'OK' if t>=target else '--'}] {target:>4} trades: {label}")

print(f"\n--- ARCHIVE: PRE_V3 ---")
print(f"  {pre_t} trades | PF 0.63 | PnL ${pre_pnl} | Status: FROZEN")

print("\n" + "=" * 60)
print(f"  Next: {max(0,10-t)} trades to Execution Verification")
print("=" * 60)
conn.close()
mt5.shutdown()
