import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 50)
print("  YESTERDAY'S TRADES (Aug 10, 2026)")
print("=" * 50)

# All trades yesterday
c.execute("SELECT COUNT(*), SUM(pnl), strategy_version FROM trades WHERE date(timestamp) = '2026-08-10' GROUP BY strategy_version")
print("\nAll Trades Yesterday:")
total = 0
total_pnl = 0
for row in c.fetchall():
    print(f"  {row[2]}: {row[0]} trades, PnL: ${row[1]:,.2f}")
    total += row[0]
    total_pnl += row[1] if row[1] else 0
print(f"  TOTAL: {total} trades, PnL: ${total_pnl:,.2f}")

# V3_REGIME yesterday
c.execute("SELECT id, pair, signal, result, pnl, timestamp, exit_time FROM trades WHERE date(timestamp) = '2026-08-10' AND strategy_version = 'V3_REGIME' ORDER BY id")
v3 = c.fetchall()
print(f"\nV3_REGIME Yesterday: {len(v3)} trades")
for t in v3:
    result = t[3] if t[3] else 'OPEN'
    pnl = f"${t[4]:,.2f}" if t[4] is not None else 'OPEN'
    print(f"  ID {t[0]}: {t[1]} {t[2]} | {result} | PnL: {pnl} | {t[5][:19]}")

# Check if ID 163 closed
c.execute("SELECT id, result, pnl, exit_price, exit_time FROM trades WHERE id = 163")
id163 = c.fetchone()
if id163:
    print(f"\nID 163 Status: {id163[1] or 'STILL OPEN'} | PnL: ${id163[2] if id163[2] else 'unrealized'} | Exit: {id163[3] or 'N/A'} | Exit Time: {str(id163[4])[:19] if id163[4] else 'N/A'}")

conn.close()
