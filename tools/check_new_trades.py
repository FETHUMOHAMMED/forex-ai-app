import sqlite3
import MetaTrader5 as mt5

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
total = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL AND date(timestamp) = '2026-07-14'")
today = c.fetchone()[0]

print("Total closed: " + str(total))
print("Closed today (July 14): " + str(today))
print()

c.execute("SELECT pair, signal, pnl, result, exit_time FROM trades WHERE pnl IS NOT NULL ORDER BY id DESC LIMIT 5")
print("Last 5 closed trades:")
for row in c.fetchall():
    print("  " + str(row[0]) + " " + str(row[1]) + " PnL=" + str(round(row[2],2)) + " " + str(row[3]) + " exit=" + str(row[4]) if row[4] else "")

mt5.initialize()
positions = mt5.positions_get()
print("\nOpen positions: " + str(len(positions) if positions else 0))
if positions:
    for p in positions:
        pnl = p.profit
        print("  " + p.symbol + " " + ("BUY" if p.type==0 else "SELL") + " @ " + str(round(p.price_open,5)) + " PnL=" + str(round(pnl,2)))
mt5.shutdown()
conn.close()
