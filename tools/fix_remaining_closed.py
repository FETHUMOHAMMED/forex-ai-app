"""Fix remaining 35 CLOSED trades"""
import sys
sys.path.insert(0, '.')
from tools.common import get_db

conn = get_db()
c = conn.cursor()

c.execute("""
    SELECT id, pair, signal, entry, exit_price, volume 
    FROM trades 
    WHERE result = 'CLOSED' AND (pnl = 0 OR pnl IS NULL)
""")
trades = c.fetchall()

print(f"Found {len(trades)} CLOSED trades with $0 P&L")
print()

breakeven = 0
for t in trades:
    id_, pair, signal, entry, exit_price, volume = t
    
    if entry and exit_price and entry == exit_price:
        c.execute("UPDATE trades SET result = 'BREAKEVEN' WHERE id = ?", (id_,))
        breakeven += 1
    
    elif entry and exit_price and volume:
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
            print(f"  ID {id_}: {pair} {signal} -> {new_result} ${pnl:.2f}")

conn.commit()

# Show final distribution
c.execute("""
    SELECT result, COUNT(*), ROUND(SUM(pnl), 2) 
    FROM trades 
    GROUP BY result 
    ORDER BY COUNT(*) DESC
""")
print(f"\nFinal Distribution:")
print("-" * 40)
for row in c.fetchall():
    print(f"  {row[0]:<12} {row[1]:<5} ${row[2] or 0:,.2f}")

print(f"\n  Breakeven trades: {breakeven + 3} total")
conn.close()
print("\nDone!")
