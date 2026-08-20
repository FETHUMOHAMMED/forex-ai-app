"""Investigate why recent trades show $0.00 P&L"""
import sys
sys.path.insert(0, '.')
from tools.common import get_db

conn = get_db()
c = conn.cursor()

print("=" * 60)
print("  TRADE DATA INVESTIGATION")
print("=" * 60)

# Check all EURUSD trades with $0 P&L
c.execute("""
    SELECT id, pair, signal, result, pnl, exit_price, entry, 
           volume, strategy_version, timestamp, exit_time
    FROM trades 
    WHERE pair = 'EURUSD' 
    ORDER BY timestamp DESC 
    LIMIT 10
""")

trades = c.fetchall()

print(f"\nLast 10 EURUSD trades:")
print("-" * 60)
for t in trades:
    id_, pair, sig, result, pnl, exit_px, entry, vol, ver, ts, exit_ts = t
    print(f"ID {id_}: {sig} | Result: {result or 'NULL'} | PnL: ${pnl or 0:.2f}")
    print(f"  Entry: {entry} | Exit: {exit_px or 'NULL'} | Vol: {vol}")
    print(f"  Version: {ver} | Time: {ts[:19] if ts else 'NULL'}")
    if exit_px and entry and vol:
        if sig == 'BUY':
            calc_pnl = (exit_px - entry) * vol * 100000
        else:
            calc_pnl = (entry - exit_px) * vol * 100000
        print(f"  Calculated PnL: ${calc_pnl:.2f}")
    print()

# Count by status
c.execute("""
    SELECT result, COUNT(*), SUM(pnl) 
    FROM trades 
    GROUP BY result 
    ORDER BY COUNT(*) DESC
""")

print("\nTrade status distribution:")
print("-" * 40)
for row in c.fetchall():
    result, count, total_pnl = row
    print(f"  {result or 'NULL':<10} {count:<5} ${total_pnl or 0:,.2f}")

# Check if $0 P&L trades are truly losses
c.execute("""
    SELECT COUNT(*) FROM trades 
    WHERE result = 'LOSS' AND pnl = 0
""")
zero_pnl_losses = c.fetchone()[0]
print(f"\nTrades marked LOSS with $0 P&L: {zero_pnl_losses}")

c.execute("""
    SELECT COUNT(*) FROM trades 
    WHERE result = 'LOSS' AND pnl != 0 AND pnl IS NOT NULL
""")
real_losses = c.fetchone()[0]
print(f"Trades marked LOSS with actual P&L: {real_losses}")

# Today's trades detail
c.execute("""
    SELECT id, pair, signal, result, pnl, entry, exit_price, volume
    FROM trades 
    WHERE date(timestamp) = date('now')
""")
today = c.fetchall()
print(f"\nToday's trades ({len(today)}):")
for t in today:
    print(f"  ID {t[0]}: {t[1]} {t[2]} | {t[3]} | PnL: ${t[4] or 0:.2f} | Entry: {t[5]} | Exit: {t[6]} | Vol: {t[7]}")

conn.close()
print("\n" + "=" * 60)
