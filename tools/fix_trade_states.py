"""Fix trades with UNKNOWN/OPEN states that should be closed"""
import sys
from pathlib import Path
sys.path.insert(0, '.')
from tools.common import get_db

def fix_unknown_trades():
    conn = get_db()
    c = conn.cursor()
    
    # Find problematic trades
    c.execute("""
        SELECT id, pair, signal, result, pnl, exit_price, exit_time, timestamp 
        FROM trades 
        WHERE result IN ('UNKNOWN', 'OPEN', '', NULL) OR result IS NULL
        ORDER BY timestamp DESC
    """)
    
    trades = c.fetchall()
    
    if not trades:
        print("No problematic trades found!")
        conn.close()
        return
    
    print(f"Found {len(trades)} trades with UNKNOWN/OPEN status:\n")
    
    for t in trades:
        id_, pair, signal, result, pnl, exit_price, exit_time, ts = t
        print(f"  ID {id_}: {pair} {signal}")
        print(f"    Timestamp: {ts}")
        print(f"    Result: {result or 'NULL'}")
        print(f"    Exit Price: {exit_price or 'NULL'}")
        print(f"    Exit Time: {exit_time or 'NULL'}")
        print(f"    PnL: {pnl or 'NULL'}")
        
        # If there's an exit_price and exit_time, it should be closed
        if exit_price and exit_time:
            c.execute("UPDATE trades SET result = 'CLOSED' WHERE id = ?", (id_,))
            print(f"    -> Fixed: Set to CLOSED")
        print()
    
    conn.commit()
    conn.close()
    print("Done! Run diagnostics again to verify.")

if __name__ == "__main__":
    fix_unknown_trades()
