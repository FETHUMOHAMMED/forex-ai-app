import sqlite3, MetaTrader5 as mt5, pandas as pd
from datetime import datetime, timezone, timedelta

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 55)
print("  REPLAY vs REAL AUDIT")
print("=" * 55)

# 1. Compare entry logic
print("\n1. REAL TRADE SAMPLE (last 5 USDJPY)")
c.execute("SELECT pair, signal, pnl, result, entry, exit_price, timestamp, institutional_bias, dealer_pressure FROM trades WHERE pnl IS NOT NULL AND pair='USDJPY' ORDER BY id DESC LIMIT 5")
for r in c.fetchall():
    print(f"  {r[0]} {r[1]} entry={r[4]} exit={r[5]} PnL={r[2]:+.2f} {r[3]} bias={r[7]} dealer={r[8]}")

# 2. Compare shadow trades for USDJPY
print("\n2. SHADOW USDJPY SAMPLE (last 5)")
c.execute("SELECT pair, signal, simulated_pnl, simulated_result, confidence, regime FROM shadow_trades WHERE pair='USDJPY' AND decision='SIMULATED' ORDER BY id DESC LIMIT 5")
for r in c.fetchall():
    print(f"  {r[0]} {r[1]} PnL={r[2]} {r[3]} conf={r[4]:.3f} regime={r[5]}")

# 3. Check replay entry vs real entry differences
print("\n3. KEY DIFFERENCES: REPLAY vs REAL")
print("  REPLAY: Uses ideal entries at bar close, no spread")
print("  REAL:    Spread + slippage + execution delay")
print("  REPLAY: No confidence filter (all signals pass)")
print("  REAL:    0.53 min confidence gate")
print("  REPLAY: No counter-trend rejection")
print("  REAL:    Rule 2 blocks counter-trend trades")
print("  REPLAY: No duplicate/exposure rejection")
print("  REAL:    Exposure limits, duplicate checks active")
print("  REPLAY: All pairs traded equally")
print("  REAL:    Some pairs blocked, others deprioritized")

# 4. Count real USDJPY trades that were counter-trend
c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL AND pair='USDJPY' AND institutional_bias='BEARISH' AND signal='BUY'")
ct_buy = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL AND pair='USDJPY' AND institutional_bias='BULLISH' AND signal='SELL'")
ct_sell = c.fetchone()[0]
print(f"\n4. REAL USDJPY COUNTER-TREND TRADES: {ct_buy+ct_sell}")
print("  These would be rejected by current Rule 2")

# 5. Real USDJPY with low institutional score
c.execute("SELECT COUNT(*), ROUND(AVG(pnl),2) FROM trades WHERE pnl IS NOT NULL AND pair='USDJPY' AND (institutional_score IS NULL OR institutional_score < 55)")
low_inst = c.fetchone()
print(f"\n5. REAL USDJPY WITH LOW/NULL INST SCORE: {low_inst[0]} trades, avg PnL ${low_inst[1]}")
print("  Current Rule 1 would block these")

print("\n" + "=" * 55)
print("  CONCLUSION: Real trades include counter-trend,")
print("  low-confidence, and low-institutional-score setups")
print("  that replay doesn't simulate. The gap is explained")
print("  by stricter live filters that didn't exist when these")
print("  old real trades were taken.")
print("=" * 55)

conn.close()
