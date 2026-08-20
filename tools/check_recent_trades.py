import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 60)
print("  RECENT TRADES INVESTIGATION")
print("=" * 60)

# All trades from last 24 hours
c.execute("""
    SELECT id, pair, signal, result, pnl, strategy_version, 
           timestamp, exit_time, environment
    FROM trades 
    WHERE timestamp >= datetime('now', '-1 day')
    ORDER BY id DESC
""")
rows = c.fetchall()
print(f"\nTrades in last 24h: {len(rows)}")
for r in rows:
    print(f"  ID {r[0]}: {r[1]} {r[2]} | Result: {r[3]} | PnL: ${r[4]} | Version: {r[5]}")
    print(f"    Entry: {r[6][:19]} | Exit: {str(r[7])[:19] if r[7] else 'OPEN'} | Env: {r[8]}")

# Today's trades specifically
c.execute("""
    SELECT id, pair, signal, result, pnl, strategy_version, timestamp 
    FROM trades 
    WHERE date(timestamp) = date('now')
""")
today = c.fetchall()
print(f"\nToday's trades (date = today): {len(today)}")
for r in today:
    print(f"  ID {r[0]}: {r[1]} {r[2]} | {r[3]} | PnL: ${r[4]} | {r[5]} | {r[6][:19]}")

# Check for V3 trades specifically
c.execute("""
    SELECT COUNT(*), SUM(pnl) FROM trades 
    WHERE strategy_version = 'V3_REGIME'
""")
v3 = c.fetchone()
print(f"\nV3_REGIME total: {v3[0]} trades, PnL: ${v3[1] or 0}")

# Check if the 2 new trades (163 vs 161) are tagged correctly
c.execute("SELECT id, strategy_version, timestamp FROM trades WHERE id > 161 ORDER BY id")
new_trades = c.fetchall()
print(f"\nNew trades since Friday (ID > 161): {len(new_trades)}")
for r in new_trades:
    print(f"  ID {r[0]}: Version={r[1]} | Time={r[2][:19]}")

conn.close()
