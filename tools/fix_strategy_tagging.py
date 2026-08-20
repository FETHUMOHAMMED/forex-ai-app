"""Fix strategy version tagging for new trades and diagnose the issue"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 60)
print("  STRATEGY VERSION TAGGING FIX")
print("=" * 60)

# 1. Fix the two new trades that should be V3_REGIME
c.execute("""
    UPDATE trades 
    SET strategy_version = 'V3_REGIME',
        environment = 'LIVE_MICRO_VALIDATION'
    WHERE id IN (162, 163)
""")
print("\n[FIXED] IDs 162, 163: PRE_V3 -> V3_REGIME")
print("        Environment: LIVE_MICRO -> LIVE_MICRO_VALIDATION")

# 2. Check what the daemon is setting as default
c.execute("PRAGMA table_info(trades)")
columns = c.fetchall()
for col in columns:
    if col[1] == 'strategy_version':
        print(f"\nstrategy_version column: default={col[4]}")

# 3. Show updated counts
c.execute("""
    SELECT strategy_version, COUNT(*), SUM(pnl)
    FROM trades
    GROUP BY strategy_version
""")
print("\nUpdated Distribution:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]} trades, PnL: ${row[2] or 0:,.2f}")

# 4. Check V3 trades detail
c.execute("""
    SELECT id, pair, signal, result, pnl, timestamp, environment
    FROM trades 
    WHERE strategy_version = 'V3_REGIME'
    ORDER BY id
""")
v3_trades = c.fetchall()
print(f"\nV3_REGIME Trades ({len(v3_trades)}):")
for t in v3_trades:
    print(f"  ID {t[0]}: {t[1]} {t[2]} | {t[3] or 'OPEN'} | PnL: ${t[4] or 0} | Env: {t[6]} | {t[5][:19]}")

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("IMPORTANT: Check daemon code for default strategy_version!")
print("The daemon is writing 'PRE_V3' as default instead of 'V3_REGIME'")
print("Look for: strategy_version = 'PRE_V3' in daemon code")
print("=" * 60)
