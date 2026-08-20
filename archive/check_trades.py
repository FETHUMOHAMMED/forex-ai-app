import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
closed = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM trades WHERE exit_price IS NULL AND pnl IS NULL")
open_trades = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL AND date(timestamp) = '2026-07-10'")
today_count = c.fetchone()[0]

c.execute("SELECT SUM(pnl) FROM trades WHERE pnl IS NOT NULL AND date(timestamp) = '2026-07-10'")
today_pnl = c.fetchone()[0]

print("Real trades:")
print("  Total closed: " + str(closed))
print("  Open: " + str(open_trades))
print("  Today (July 10): " + str(today_count) + " trades, PnL: " + str(round(today_pnl, 2) if today_pnl else "0"))

c.execute("SELECT COUNT(*) FROM shadow_trades")
shadow = c.fetchone()[0]
print("\nShadow trades: " + str(shadow))
print("TOTAL data points: " + str(closed + shadow))

c.execute("SELECT pair, signal, pnl, result FROM trades WHERE pnl IS NOT NULL ORDER BY id DESC LIMIT 5")
print("\nLast 5 trades:")
for row in c.fetchall():
    print("  " + str(row[0]) + " " + str(row[1]) + " PnL=" + str(round(row[2],2)) + " " + str(row[3]))

conn.close()
