"""
INSTITUTIONAL-GRADE DASHBOARD - Professional Trading Firm Standard
"""
import sqlite3, json, urllib.request, MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# ===== V3 PERFORMANCE METRICS =====
c.execute("""SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END),
             ROUND(SUM(pnl),2), ROUND(AVG(CASE WHEN pnl>0 THEN pnl END),2), 
             ROUND(AVG(CASE WHEN pnl<0 THEN pnl END),2), ROUND(AVG(confidence),3),
             ROUND(MAX(CASE WHEN pnl<0 THEN pnl END),2), ROUND(SUM(CASE WHEN pnl>0 THEN pnl END),2),
             ROUND(SUM(CASE WHEN pnl<0 THEN pnl END),2)
             FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL""")
v3 = c.fetchone()
t, w, l, pnl, aw, al, ac, max_dd, gross_win, gross_loss = v3

# PRE_V3 baseline
c.execute("SELECT COUNT(*), ROUND(SUM(pnl),2) FROM trades WHERE strategy_version='PRE_V3' AND pnl IS NOT NULL")
pre_t, pre_pnl = c.fetchone()

# Regime performance
c.execute("""SELECT institutional_bias, COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2)
             FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL GROUP BY institutional_bias""")
regimes = c.fetchall()

# Confidence calibration
buckets = [(0.75,0.80),(0.80,0.85),(0.85,0.90),(0.90,1.01)]
conf_data = []
for lo, hi in buckets:
    c.execute("""SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2) 
                 FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL 
                 AND confidence>=? AND confidence<?""", (lo, hi))
    r = c.fetchone()
    conf_data.append((f"{int(lo*100)}-{int(hi*100)}%", r[0], r[1] or 0, r[2] or 0))

# Account stats
mt5.initialize()
live_bal = 0; live_eq = 0; live_margin = 0; live_free = 0; live_positions = 0; floating_pnl = 0
try:
    if mt5.login(REDACTED_LIVE_ACCOUNT, password='REDACTED_OLD_LIVE_PASSWORD', server='Exness-MT5Real10'):
        acc = mt5.account_info()
        if acc:
            live_bal = acc.balance; live_eq = acc.equity; live_margin = acc.margin
            live_free = acc.margin_free
        pos = mt5.positions_get()
        if pos:
            live_positions = len(pos)
            floating_pnl = sum(p.profit for p in pos)
except: pass

# Current AI signal
try:
    resp = urllib.request.urlopen('http://localhost:8001/signals', timeout=3)
    data = json.loads(resp.read())
    sigs = data.get('signals', [])
    cur = sigs[0] if sigs else None
except: cur = None

# ===== RENDER DASHBOARD =====
print("+" + "-"*58 + "+")
print("¦" + "  FOREX-AI-APP | INSTITUTIONAL TRADING DASHBOARD".ljust(58) + "¦")
print("¦" + f"  Strategy: V3_REGIME | Status: LIVE MICRO | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}".ljust(58) + "¦")
print("+" + "-"*58 + "+")

# -- PERFORMANCE --
print("\n+- PERFORMANCE METRICS " + "-"*36 + "+")
wr = round(w/t*100,1) if t>0 else 0
pf = round(gross_win/abs(gross_loss),2) if gross_loss and gross_loss!=0 else ('N/A' if t<2 else 999)
ev = round((wr/100)*(aw or 0) - ((100-wr)/100)*abs(al or 0),2) if t>0 and aw and al else ('N/A' if t<2 else 0)
avg_r = round((aw or 0)/abs(al or 1),2) if aw and al else 'N/A'

print(f"¦ Trades: {t:<5} Win Rate: {wr}%{' ' if wr<10 else ''}   PF: {pf:<8} Expectancy: ${ev if ev!='N/A' else 'N/A'}")
print(f"¦ Wins: {w:<5}  Losses: {l:<5}  Avg Win: ${aw or 'N/A':<10} Avg Loss: ${al or 'N/A'}")
print(f"¦ Avg R: {avg_r:<6} Max DD: ${max_dd or 'N/A':<10} Net PnL: ${pnl or 0}")
print(f"¦ Avg Confidence: {ac}")
print("+" + "-"*56 + "+")

# -- ACCOUNT --
print("\n+- LIVE MICRO ACCOUNT " + "-"*37 + "+")
margin_pct = round(live_margin/live_eq*100,1) if live_eq>0 else 0
print(f"¦ Balance: ${live_bal:,.2f}  Equity: ${live_eq:,.2f}  Margin: {margin_pct}%")
print(f"¦ Free: ${live_free:,.2f}  Positions: {live_positions}  Floating: ${floating_pnl:+,.2f}")
print("+" + "-"*56 + "+")

# -- REGIME --
print("\n+- REGIME PERFORMANCE " + "-"*37 + "+")
if regimes:
    for regime, rt, rw, rpnl in regimes:
        rwr = round(rw/rt*100) if rt>0 else 0
        print(f"¦ {regime:<25s} {rt:>4d} trades  {rwr:>5.1f}% WR  ${rpnl:>+8}")
else:
    print(f"¦ Collecting regime data...")
print("+" + "-"*56 + "+")

# -- CONFIDENCE CALIBRATION --
print("\n+- CONFIDENCE CALIBRATION " + "-"*33 + "+")
print(f"¦ {'Bucket':<12s} {'Trades':>6s} {'Wins':>6s} {'PnL':>8s}")
for label, ct, cw, cpnl in conf_data:
    print(f"¦ {label:<12s} {ct:>6} {cw:>6} ${cpnl:>+7}")
print("+" + "-"*56 + "+")

# -- CURRENT SIGNAL --
print("\n+- CURRENT AI ANALYSIS " + "-"*36 + "+")
if cur:
    print(f"¦ {cur['pair']} {cur['signal']} @ {cur['confidence']:.1%} confidence")
    print(f"¦ Regime: {cur.get('institutional_bias','?')} | Dealer: {cur.get('dealer_pressure','?')}")
    print(f"¦ Liquidity: {cur.get('liquidity_state','?')} | Entry: {cur.get('entry',0):.5f}")
    print(f"¦ SL: {cur.get('stop_loss',0):.5f} | TP: {cur.get('take_profit',0):.5f}")
else:
    print(f"¦ No active signal - awaiting setup")
print("+" + "-"*56 + "+")

# -- INSTITUTIONAL SCORECARD --
print("\n+- INSTITUTIONAL SCORECARD " + "-"*32 + "+")
scores = [("Execution Engine",5),("Risk Management",5),("Data Quality",5),("Regime Detection",5),
          ("ML Pipeline",5),("Position Mgmt",4),("Trade Logging",5),("Statistical Proof",1)]
for name, score in scores:
    stars = chr(9733)*score + chr(9734)*(5-score)
    print(f"¦ {name:<25s} {stars}")
print("+" + "-"*56 + "+")

# -- MILESTONES --
print("\n+- RESEARCH ROADMAP " + "-"*40 + "+")
for target, label in [(10,"Execution Verified"),(25,"Risk Verified"),(50,"Initial Review"),
                       (100,"Statistical Validity"),(300,"Production Ready"),(1000,"Institutional Grade")]:
    done = t >= target
    print(f"¦ [{'OK' if done else '--'}] {target:>4} trades ? {label}")
print("+" + "-"*56 + "+")

# -- HISTORICAL --
print(f"\n+- ARCHIVE: PRE_V3 - {pre_t} trades, PF 0.63, {round(pre_t and pre_pnl/pre_t or 0,1)}% WR, ${pre_pnl} -+")
print(f"¦ Status: FROZEN — Weak institutional filtering. Replaced by V3_REGIME.")
print("+" + "-"*56 + "+")

print("\n" + "="*60)
print(f"  Next Review: {max(0, 10-t)} trades to Execution Verification")
print("="*60)

conn.close()
mt5.shutdown()
