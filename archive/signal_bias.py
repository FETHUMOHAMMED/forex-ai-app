import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
c.execute("SELECT signal, COUNT(*) FROM trades WHERE pnl IS NOT NULL GROUP BY signal")
print("ALL TRADES:")
for row in c.fetchall():
    print("  " + str(row[0]) + ": " + str(row[1]))
c.execute("SELECT signal, COUNT(*) FROM trades WHERE strategy_version='V3_REGIME' GROUP BY signal")
print("\nV3_REGIME:")
for row in c.fetchall():
    print("  " + str(row[0]) + ": " + str(row[1]))
conn.close()
