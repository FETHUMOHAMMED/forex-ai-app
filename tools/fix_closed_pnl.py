"""Fix CLOSED trades that have $0 P&L but valid entry/exit prices"""
import sys
sys.path.insert(0, '.')
from tools.common import get_db

def fix_pnl():
    conn = get_db()
    c = conn.cursor()
    
    # Find CLOSED trades with valid entry/exit but $0 P&L
    c.execute("""
        SELECT id, pair, signal, entry, exit_price, volume, result
        FROM trades 
        WHERE result IN ('CLOSED', 'SYNCED', 'AUTO_SYNCED')
        AND entry IS NOT NULL 
        AND exit_price IS NOT NULL 
        AND entry != exit_price
        AND (pnl = 0 OR pnl IS NULL)
    """)
    
    trades = c.fetchall()
    
    if not trades:
        print("No trades to fix!")
        conn.close()
        return
    
    print(f"Fixing {len(trades)} trades with missing P&L:\n")
    
    fixed = 0
    for t in trades:
        id_, pair, signal, entry, exit_price, volume, result = t
        
        # Calculate P&L based on signal direction
        if signal == 'BUY':
            pnl = (exit_price - entry) * volume * 100000
        elif signal == 'SELL':
            pnl = (entry - exit_price) * volume * 100000
        else:
            continue
        
        # Determine actual result
        if pnl > 0:
            new_result = 'WIN'
        elif pnl < 0:
            new_result = 'LOSS'
        else:
            new_result = 'BREAKEVEN'
        
        # Calculate PnL percentage
        pnl_percent = (pnl / (entry * volume * 100000)) * 100 if entry and volume else 0
        
        c.execute("""
            UPDATE trades 
            SET pnl = ?, pnl_percent = ?, result = ?
            WHERE id = ?
        """, (round(pnl, 2), round(pnl_percent, 4), new_result, id_))
        
        print(f"  ID {id_}: {pair} {signal} | {result} -> {new_result}")
        print(f"    Entry: {entry} | Exit: {exit_price} | Vol: {volume}")
        print(f"    PnL: $0.00 -> ${pnl:.2f}")
        fixed += 1
    
    conn.commit()
    conn.close()
    
    print(f"\nFixed {fixed} trades!")
    print("Run diagnostics or strategy review to see updated stats.")

if __name__ == "__main__":
    fix_pnl()
