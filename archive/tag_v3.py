import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
try:
    c.execute("ALTER TABLE trades ADD COLUMN strategy_version TEXT DEFAULT 'PRE_V3'")
except: pass
c.execute("UPDATE trades SET strategy_version='V3_REGIME' WHERE date(timestamp) >= '2026-08-03'")
conn.commit()
c.execute("SELECT strategy_version, COUNT(*) FROM trades WHERE pnl IS NOT NULL GROUP BY strategy_version")
print("Trades by version:")
for row in c.fetchall():
    print("  " + str(row[0]) + ": " + str(row[1]))
conn.close()
