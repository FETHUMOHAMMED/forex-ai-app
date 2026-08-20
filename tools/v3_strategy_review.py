"""V3 Strategy Parameter Review"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import get_db, check_mt5
from datetime import datetime, timezone

def main():
    print("=" * 70)
    print("  V3_REGIME STRATEGY REVIEW")
    print("=" * 70)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Overall stats by strategy version
    cursor.execute("""
        SELECT 
            strategy_version,
            COUNT(*) as trades,
            SUM(pnl) as total_pnl,
            ROUND(AVG(pnl), 2) as avg_pnl,
            ROUND(CAST(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1) as win_rate,
            ROUND(AVG(confidence), 3) as avg_confidence,
            ROUND(SUM(CASE WHEN result='WIN' THEN pnl ELSE 0 END) / 
                  NULLIF(ABS(SUM(CASE WHEN result='LOSS' THEN pnl ELSE 0 END)), 0), 2) as profit_factor
        FROM trades 
        WHERE result IS NOT NULL AND result != ''
        GROUP BY strategy_version
        ORDER BY COUNT(*) DESC
    """)
    
    print("\n--- STRATEGY COMPARISON ---")
    print(f"{'Version':<15} {'Trades':<8} {'Win Rate':<10} {'P&L':<15} {'Avg P&L':<12} {'PF':<8} {'Avg Conf':<10}")
    print("-" * 70)
    
    for row in cursor.fetchall():
        version, trades, pnl, avg_pnl, wr, conf, pf = row
        print(f"{version:<15} {trades:<8} {wr or 0:<9.1f}% ${pnl or 0:<13,.2f} ${avg_pnl or 0:<10.2f} {pf or 0:<7.2f} {conf or 0:<9.3f}")
    
    # V3 trades detail
    print("\n--- V3_REGIME TRADES ---")
    cursor.execute("""
        SELECT pair, signal, result, pnl, confidence, regime, timestamp
        FROM trades 
        WHERE strategy_version = 'V3_REGIME'
        ORDER BY timestamp DESC
    """)
    
    v3_trades = cursor.fetchall()
    if v3_trades:
        print(f"{'Date':<12} {'Pair':<10} {'Signal':<8} {'Result':<8} {'P&L':<12} {'Conf':<8} {'Regime':<15}")
        print("-" * 70)
        for trade in v3_trades:
            pair, signal, result, pnl, conf, regime, ts = trade
            date_str = ts[:10] if ts else "N/A"
            print(f"{date_str:<12} {pair:<10} {signal:<8} {result or 'OPEN':<8} ${pnl or 0:<11,.2f} {conf or 0:<7.3f} {regime or 'N/A':<15}")
    else:
        print("  No V3_REGIME trades yet")
    
    # Regime distribution
    print("\n--- REGIME DISTRIBUTION (All Trades) ---")
    cursor.execute("""
        SELECT regime, COUNT(*), ROUND(AVG(pnl), 2)
        FROM trades 
        WHERE regime IS NOT NULL
        GROUP BY regime
        ORDER BY COUNT(*) DESC
    """)
    
    for row in cursor.fetchall():
        regime, count, avg_pnl = row
        bar = "#" * min(count, 30)
        print(f"  {regime or 'Unknown':<20} {count:<5} avg P&L: ${avg_pnl or 0:<10,.2f} {bar}")
    
    # Pair performance
    print("\n--- PAIR PERFORMANCE (All Trades) ---")
    cursor.execute("""
        SELECT pair, COUNT(*), SUM(pnl), 
               ROUND(CAST(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1)
        FROM trades 
        WHERE result IS NOT NULL AND result != ''
        GROUP BY pair
        ORDER BY SUM(pnl) DESC
    """)
    
    print(f"{'Pair':<10} {'Trades':<8} {'P&L':<15} {'Win Rate':<10}")
    print("-" * 45)
    for row in cursor.fetchall():
        pair, count, pnl, wr = row
        print(f"{pair:<10} {count:<8} ${pnl or 0:<13,.2f} {wr or 0:<9.1f}%")
    
    conn.close()
    
    # Recommendations
    print("\n--- RECOMMENDATIONS ---")
    print("  1. Let V3_REGIME reach 10 trades before first review")
    print("  2. Compare V3 win rate vs PRE_V3 (25% baseline)")
    print("  3. Monitor regime distribution for bias")
    print("  4. At 50 trades, run full statistical validation")
    print("  5. Target: PF > 1.5, Win Rate > 40%, Avg P&L positive")
    print("=" * 70)

if __name__ == "__main__":
    main()
