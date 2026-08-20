"""Add proper account/environment filtering to trades table"""
import sys
sys.path.insert(0, '.')
from tools.common import get_db

def add_account_fields():
    conn = get_db()
    c = conn.cursor()
    
    # Check existing columns
    c.execute("PRAGMA table_info(trades)")
    columns = [col[1] for col in c.fetchall()]
    
    # Add missing columns
    additions = []
    if 'account_id' not in columns:
        additions.append("account_id INTEGER DEFAULT REDACTED_LIVE_ACCOUNT")
    if 'environment' not in columns:
        additions.append("environment TEXT DEFAULT 'LIVE_MICRO'")
    if 'strategy_version' in columns and 'strategy_version' not in [c[1] for c in c.execute("PRAGMA table_info(trades)").fetchall()]:
        pass  # Already exists
    
    for addition in additions:
        try:
            c.execute(f"ALTER TABLE trades ADD COLUMN {addition}")
            print(f"? Added {addition.split()[0]}")
        except Exception as e:
            print(f"  {addition.split()[0]}: {e}")
    
    # Backfill account_id for existing trades
    c.execute("UPDATE trades SET account_id = REDACTED_LIVE_ACCOUNT WHERE account_id IS NULL")
    c.execute("UPDATE trades SET environment = 'LIVE_MICRO' WHERE environment IS NULL")
    
    # Tag PRE_V3 trades with demo environment if they have demo indicators
    c.execute("""
        UPDATE trades SET environment = 'DEMO' 
        WHERE (pnl < -100 OR pnl > 100) 
        AND strategy_version = 'PRE_V3'
    """)
    
    conn.commit()
    
    # Show current distribution
    print("\nTrade Distribution by Environment & Strategy:")
    print("-" * 60)
    
    c.execute("""
        SELECT environment, strategy_version, account_id, COUNT(*), ROUND(SUM(pnl), 2)
        FROM trades
        GROUP BY environment, strategy_version, account_id
        ORDER BY COUNT(*) DESC
    """)
    
    for row in c.fetchall():
        env, strategy, account, count, pnl = row
        print(f"  {env:<15} {strategy:<15} {account:<12} {count:<5} ${pnl or 0:,.2f}")
    
    conn.close()
    
    print("\n? Account filtering ready!")
    print("  V3_REGIME trades will be tagged with:")
    print("    account_id: REDACTED_LIVE_ACCOUNT")
    print("    environment: LIVE_MICRO")
    print("    strategy_version: V3_REGIME")

if __name__ == "__main__":
    add_account_fields()
