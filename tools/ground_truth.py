import sqlite3
c = sqlite3.connect('ai-service/trades.db')

print("--- TODAY'S TRADES ---")
rows = c.execute("""
    SELECT id, pair, signal, result, pnl, strategy_version, timestamp 
    FROM trades WHERE date(timestamp) = date('now') 
    ORDER BY id DESC
""").fetchall()
for r in rows:
    print(f"  ID {r[0]}: {r[1]} {r[2]} | {r[3]} | PnL: {r[4]} | Version: {r[5]} | {r[6][:19]}")

print(f"\n--- V3_REGIME TOTAL ---")
v3 = c.execute("SELECT COUNT(*), COALESCE(SUM(pnl), 0) FROM trades WHERE strategy_version = 'V3_REGIME'").fetchone()
print(f"  Trades: {v3[0]}, PnL: ${v3[1]:,.2f}")

print(f"\n--- V3_REGIME THIS WEEK (since {''} )---")
v3_week = c.execute("""
    SELECT COUNT(*), COALESCE(SUM(pnl), 0) 
    FROM trades WHERE strategy_version = 'V3_REGIME' 
    AND timestamp >= date('now', '-6 days')
""").fetchone()
print(f"  Trades: {v3_week[0]}, PnL: ${v3_week[1]:,.2f}")

print(f"\n--- ALL TRADES THIS WEEK ---")
all_week = c.execute("""
    SELECT COUNT(*), COALESCE(SUM(pnl), 0), strategy_version 
    FROM trades WHERE timestamp >= date('now', '-6 days')
    GROUP BY strategy_version
""").fetchall()
for r in all_week:
    print(f"  {r[2]}: {r[0]} trades, PnL: ${r[1]:,.2f}")

print(f"\n--- NULL VALUES CHECK ---")
nulls = c.execute("""
    SELECT COUNT(*) FROM trades WHERE pnl IS NULL AND exit_time IS NOT NULL
""").fetchone()
print(f"  Trades with NULL pnl but have exit_time: {nulls[0]}")

nulls2 = c.execute("""
    SELECT COUNT(*) FROM trades WHERE result IS NULL OR result = ''
""").fetchone()
print(f"  Trades with NULL/empty result: {nulls2[0]}")

c.close()
