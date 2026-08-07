"""Verify Trading State - Check for issues in current positions"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import get_db, check_mt5

def main():
    print("=" * 50)
    print("  TRADING STATE VERIFICATION")
    print("=" * 50)
    
    # Check MT5 connection
    mt5_status = check_mt5()
    print(f"\nMT5 Connection: {'PASS' if mt5_status['connected'] else 'FAIL'}")
    
    if not mt5_status['connected']:
        print("Cannot verify trading state without MT5 connection")
        return
    
    # Check database
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Total trades
        cursor.execute("SELECT COUNT(*) FROM trades")
        total = cursor.fetchone()[0]
        print(f"\nTotal Trades: {total}")
        
        # Recent trades (last 24h)
        cursor.execute("SELECT COUNT(*) FROM trades WHERE timestamp >= datetime('now', '-1 day')")
        recent = cursor.fetchone()[0]
        print(f"Recent (24h): {recent}")
        
        # Win rate
        cursor.execute("SELECT COUNT(*), SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) FROM trades")
        total_wins = cursor.fetchone()
        if total_wins[0] > 0:
            win_rate = (total_wins[1] / total_wins[0]) * 100
            print(f"Win Rate: {win_rate:.1f}%")
        
        # Total PnL
        cursor.execute("SELECT SUM(pnl) FROM trades")
        total_pnl = cursor.fetchone()[0] or 0
        print(f"Total PnL: ${total_pnl:.2f}")
        
        # Pairs traded
        cursor.execute("SELECT DISTINCT pair FROM trades")
        pairs = [row[0] for row in cursor.fetchall()]
        print(f"Pairs Traded: {', '.join(pairs)}")
        
        conn.close()
    except Exception as e:
        print(f"\nDatabase Error: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
