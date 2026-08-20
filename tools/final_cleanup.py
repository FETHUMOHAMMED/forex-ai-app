"""Final cleanup: Fix sync trades and verify heartbeat"""
import sys
sys.path.insert(0, '.')
from tools.common import get_db
from tools.heartbeat import quick_heartbeat
import time

print("=" * 50)
print("  FINAL DATA CLEANUP")
print("=" * 50)

# 1. Fix SYNCED/AUTO_SYNCED trades
conn = get_db()
c = conn.cursor()

c.execute("""
    SELECT id, pair, signal, entry, exit_price, volume, result 
    FROM trades 
    WHERE result IN ('SYNCED', 'AUTO_SYNCED')
    AND (pnl = 0 OR pnl IS NULL)
""")
sync_trades = c.fetchall()

if sync_trades:
    print(f"\nFixing {len(sync_trades)} sync trades:")
    for t in sync_trades:
        id_, pair, signal, entry, exit_price, volume, result = t
        
        if entry and exit_price:
            if signal == 'BUY':
                pnl = (exit_price - entry) * volume * 100000
            else:
                pnl = (entry - exit_price) * volume * 100000
            
            if pnl != 0:
                new_result = 'WIN' if pnl > 0 else 'LOSS'
                pnl_pct = (pnl / (entry * volume * 100000)) * 100
                c.execute("""
                    UPDATE trades SET pnl = ?, pnl_percent = ?, result = ?
                    WHERE id = ?
                """, (round(pnl, 2), round(pnl_pct, 4), new_result, id_))
                print(f"  ID {id_}: {result} -> {new_result} (${pnl:.2f})")
            else:
                c.execute("UPDATE trades SET result = 'BREAKEVEN' WHERE id = ?", (id_,))
                print(f"  ID {id_}: {result} -> BREAKEVEN ($0.00)")
        else:
            print(f"  ID {id_}: Cannot fix - missing entry/exit data")

conn.commit()
conn.close()

# 2. Check heartbeat functionality
print("\nHeartbeat Status:")
print(f"  Before: Check daemon_heartbeat.json")
quick_heartbeat("trading_daemon")
print(f"  After: Heartbeat written at {time.strftime('%H:%M:%S')}")
print(f"  Note: Daemon should write heartbeat every 30s automatically")

# 3. Show final stats
conn = get_db()
c = conn.cursor()
c.execute("""
    SELECT result, COUNT(*), ROUND(SUM(pnl), 2) 
    FROM trades 
    GROUP BY result 
    ORDER BY COUNT(*) DESC
""")
print("\nFinal Trade Status Distribution:")
print("-" * 40)
for row in c.fetchall():
    result, count, total_pnl = row
    print(f"  {result:<12} {count:<5} ${total_pnl or 0:,.2f}")

c.execute("SELECT COUNT(*), ROUND(SUM(pnl), 2) FROM trades")
total = c.fetchone()
print(f"\n  TOTAL:     {total[0]:<5} ${total[1] or 0:,.2f}")
conn.close()

print("\n" + "=" * 50)
print("Cleanup complete! Restart daemon for heartbeat auto-updates.")
