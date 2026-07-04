import sqlite3
conn = sqlite3.connect('trades.db')
c = conn.cursor()

try:
    c.execute("ALTER TABLE trades ADD COLUMN strategy_version TEXT DEFAULT 'v1_old_system'")
    print('Added strategy_version column')
except:
    print('Column already exists')

c.execute("UPDATE trades SET strategy_version = 'v1_old_system' WHERE strategy_version IS NULL OR strategy_version = ''")
print(f'Tagged {c.rowcount} trades as v1_old_system')

c.execute("UPDATE trades SET strategy_version = 'v2_optimized' WHERE timestamp >= '2026-06-30' AND pair IN ('USDCAD','USDCHF','USDJPY')")
print(f'Tagged {c.rowcount} trades as v2_optimized')

conn.commit()

c.execute("SELECT strategy_version, COUNT(*), SUM(pnl) FROM trades WHERE pnl IS NOT NULL GROUP BY strategy_version")
for r in c.fetchall():
    if r[2]:
        print(f"{r[0]}: {r[1]} trades, PnL=${r[2]:.2f}")
    else:
        print(f"{r[0]}: {r[1]} trades")

conn.close()