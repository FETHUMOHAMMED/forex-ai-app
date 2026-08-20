"""Trades by Account - Real money vs Paper"""
import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# Add account column if missing
try:
    c.execute("ALTER TABLE trades ADD COLUMN account_name TEXT DEFAULT 'UNKNOWN'")
except: pass

# Tag accounts based on ticket ranges or account field
c.execute("UPDATE trades SET account_name='Demo2' WHERE account_name='UNKNOWN' AND ticket IS NOT NULL AND ticket < 3000000000")
c.execute("UPDATE trades SET account_name='Live_Micro' WHERE account_name='UNKNOWN' AND ticket IS NOT NULL AND ticket >= 500000000")
conn.commit()

print("=" * 55)
print("  TRADES BY ACCOUNT")
print("=" * 55)

c.execute("SELECT account_name, COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2), strategy_version FROM trades WHERE pnl IS NOT NULL GROUP BY account_name, strategy_version ORDER BY account_name")
for row in c.fetchall():
    name, t, w, pnl, ver = row
    wr = w/t*100 if t > 0 else 0
    acct_type = "REAL MONEY" if "Live" in str(name) else "PAPER/DEMO"
    print(f"  {str(name):15s} [{acct_type:12s}] {str(ver):10s}: {t:3d} trades, {wr:.0f}% WR, PnL ${pnl}")

print("\n" + "=" * 55)
print("  SUMMARY:")
c.execute("SELECT CASE WHEN account_name LIKE '%Live%' THEN 'REAL MONEY' ELSE 'PAPER/DEMO' END as type, COUNT(*), ROUND(SUM(pnl),2) FROM trades WHERE pnl IS NOT NULL GROUP BY type")
for row in c.fetchall():
    print(f"  {row[0]:15s}: {row[1]} trades, PnL ${row[2]}")
print("=" * 55)
conn.close()
