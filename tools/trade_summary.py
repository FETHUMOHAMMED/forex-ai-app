import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 55)
print("  TRADE SUMMARY")
print("=" * 55)

# All trades
c.execute("SELECT COUNT(*) FROM trades")
total = c.fetchone()[0]

# By status
c.execute("""
    SELECT 
        CASE 
            WHEN result LIKE 'LEGACY%' THEN 'LEGACY_INVALID'
            WHEN result = 'EXECUTION_EXCEPTION' THEN 'EXECUTION_EXCEPTION'
            WHEN result IN ('WIN','LOSS','BREAKEVEN') THEN 'CLOSED'
            WHEN result IS NULL OR result = '' OR result = 'OPEN' THEN 'OPEN'
            ELSE result
        END as status,
        COUNT(*) as count
    FROM trades
    GROUP BY status
    ORDER BY count DESC
""")
print("\nAll Trades:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}")

# V3 Live_Micro only
c.execute("""
    SELECT 
        CASE 
            WHEN result LIKE 'LEGACY%' THEN 'LEGACY_INVALID'
            WHEN result = 'EXECUTION_EXCEPTION' THEN 'EXECUTION_EXCEPTION'
            WHEN result IN ('WIN','LOSS','BREAKEVEN') THEN 'CLOSED'
            WHEN result IS NULL OR result = '' OR result = 'OPEN' THEN 'OPEN'
            ELSE result
        END as status,
        COUNT(*) as count
    FROM trades
    WHERE strategy_version = 'V3_REGIME' AND account = 'Live_Micro'
    GROUP BY status
""")
print("\nV3 Live_Micro:")
v3_rows = c.fetchall()
for row in v3_rows:
    print(f"  {row[0]}: {row[1]}")

# Open positions from MT5
import MetaTrader5 as mt5
mt5.initialize()
positions = mt5.positions_get()
print(f"\nMT5 Open Positions: {len(positions) if positions else 0}")
if positions:
    for p in positions:
        print(f"  Ticket {p.ticket}: {p.symbol} {p.type} Vol:{p.volume} Profit:${p.profit:.2f}")
mt5.shutdown()

conn.close()
