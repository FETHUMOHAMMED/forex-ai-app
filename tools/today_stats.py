import sqlite3
from datetime import datetime

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

today = datetime.now().strftime('%Y-%m-%d')
today_display = datetime.now().strftime('%b %d, %Y')

print("=" * 50)
print(f"  TODAY'S TRADES ({today_display})")
print("=" * 50)

# All trades today
c.execute("SELECT COUNT(*), COALESCE(SUM(pnl), 0) FROM trades WHERE date(timestamp) = ?", (today,))
total = c.fetchone()
print(f"\nTotal Trades Today: {total[0]}")
print(f"Total PnL: ${total[1]:,.2f}")

# By strategy
c.execute("SELECT strategy_version, COUNT(*), COALESCE(SUM(pnl), 0) FROM trades WHERE date(timestamp) = ? AND result NOT LIKE 'LEGACY%' GROUP BY strategy_version", (today,))
print("\nBy Strategy (excludes LEGACY_INVALID):")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]} trades, PnL: ${row[2]:,.2f}")

# Detail
c.execute("SELECT id, pair, signal, result, pnl, strategy_version, timestamp FROM trades WHERE date(timestamp) = ? AND result NOT LIKE 'LEGACY%' ORDER BY id", (today,))
rows = c.fetchall()
if rows:
    print(f"\nDetail:")
    for r in rows:
        result = r[3] if r[3] else 'OPEN'
        pnl = f"${r[4]:,.2f}" if r[4] is not None else 'OPEN'
        print(f"  ID {r[0]}: {r[1]} {r[2]} | {result} | PnL: {pnl} | {r[5]}")
else:
    print("\n  No valid trades today")

# Open positions (exclude phantom/legacy)
c.execute("""
    SELECT COUNT(*) FROM trades 
    WHERE exit_time IS NULL AND exit_price IS NULL 
    AND result NOT LIKE 'LEGACY%'
    AND mt5_position_id IS NOT NULL
""")
open_count = c.fetchone()[0]
print(f"\nCurrently Open (valid): {open_count} trades")

conn.close()
