"""V3 Daily Report Generator"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import get_db
from datetime import datetime

def main():
    print("=" * 50)
    print("  V3 DAILY REPORT")
    print("=" * 50)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Today's trades
        cursor.execute("SELECT COUNT(*) FROM trades WHERE date(timestamp) = date('now')")
        today_trades = cursor.fetchone()[0]
        print(f"\nToday's Trades: {today_trades}")
        
        # Today's PnL
        cursor.execute("SELECT SUM(pnl) FROM trades WHERE date(timestamp) = date('now')")
        today_pnl = cursor.fetchone()[0] or 0
        print(f"Today's PnL: ${today_pnl:.2f}")
        
        # This week's stats
        cursor.execute("SELECT COUNT(*), SUM(pnl) FROM trades WHERE timestamp >= datetime('now', '-7 days')")
        week_stats = cursor.fetchone()
        print(f"\nThis Week:")
        print(f"  Trades: {week_stats[0]}")
        print(f"  PnL: ${week_stats[1] or 0:.2f}")
        
        # Best/Worst trades
        cursor.execute("SELECT pair, pnl, timestamp FROM trades ORDER BY pnl DESC LIMIT 3")
        best = cursor.fetchall()
        print(f"\nBest Trades:")
        for trade in best:
            print(f"  {trade[0]}: ${trade[1]:.2f} ({trade[2][:10]})")
        
        cursor.execute("SELECT pair, pnl, timestamp FROM trades ORDER BY pnl ASC LIMIT 3")
        worst = cursor.fetchall()
        print(f"\nWorst Trades:")
        for trade in worst:
            print(f"  {trade[0]}: ${trade[1]:.2f} ({trade[2][:10]})")
        
        # Account breakdown
        cursor.execute("SELECT account, COUNT(*), SUM(pnl) FROM trades GROUP BY account")
        accounts = cursor.fetchall()
        print(f"\nAccount Breakdown:")
        for acc in accounts:
            print(f"  {acc[0]}: {acc[1]} trades, ${acc[2] or 0:.2f}")
        
        conn.close()
    except Exception as e:
        print(f"\nDatabase Error: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
