"""Add strategy_version column if missing and backfill data"""
import sys
from pathlib import Path
sys.path.insert(0, '.')
from tools.common import get_db

def migrate():
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(trades)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'strategy_version' not in columns:
        print("Adding strategy_version column...")
        cursor.execute("ALTER TABLE trades ADD COLUMN strategy_version TEXT DEFAULT 'PRE_V3'")
        conn.commit()
        print("? Column added")
    else:
        print("? strategy_version column already exists")
    
    # Show distribution
    cursor.execute("""
        SELECT strategy_version, COUNT(*), SUM(pnl), 
               ROUND(CAST(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1)
        FROM trades 
        GROUP BY strategy_version
        ORDER BY COUNT(*) DESC
    """)
    
    print("\nStrategy Version Distribution:")
    print("-" * 60)
    print(f"{'Version':<20} {'Trades':<10} {'P&L':<15} {'Win Rate':<10}")
    print("-" * 60)
    
    for row in cursor.fetchall():
        version, count, pnl, win_rate = row
        print(f"{version:<20} {count:<10} ${pnl or 0:<14.2f} {win_rate or 0:<9.1f}%")
    
    conn.close()

if __name__ == "__main__":
    migrate()
