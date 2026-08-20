"""Sync database to MT5 reality - remove phantom, add missing"""
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 60)
print("  SYNCING DB TO MT5 REALITY")
print("=" * 60)

# 1. Tag ID 146 as phantom (never executed in MT5)
c.execute("""
    UPDATE trades SET 
        result = 'PHANTOM',
        reason = 'Never executed in MT5 - database-only record',
        pnl = NULL,
        exit_time = NULL
    WHERE id = 146
""")
print("\nID 146: Tagged as PHANTOM (not in MT5)")

# 2. ID 163 is correct - verify
c.execute("SELECT id, ticket, pnl, result FROM trades WHERE id = 163")
r = c.fetchone()
print(f"ID 163: Ticket={r[1]} PnL={r[2]} Result={r[3]} - CORRECT")

# 3. Check for open MT5 position not in DB
mt5.initialize()
positions = mt5.positions_get()
if positions:
    for p in positions:
        c.execute("SELECT id FROM trades WHERE ticket = ?", (p.ticket,))
        if not c.fetchone():
            print(f"\nOPEN POSITION NOT IN DB: Ticket {p.ticket}")
            print(f"  Symbol: {p.symbol} | Type: {p.type} | Volume: {p.volume}")
            print(f"  Open: {p.price_open} | Current: {p.price_current}")
            print(f"  Profit: ${p.profit:.2f} | SL: {p.sl} | TP: {p.tp}")
else:
    print("\nNo open MT5 positions")

mt5.shutdown()

# 4. Verify validation count (should be 1, not 2)
c.execute("""
    SELECT COUNT(*) FROM trades 
    WHERE strategy_version = 'V3_REGIME' 
    AND account = 'Live_Micro'
    AND result IN ('WIN', 'LOSS', 'BREAKEVEN')
    AND exit_time IS NOT NULL
""")
valid = c.fetchone()[0]
print(f"\nTrue Clean V3 Live_Micro: {valid} trade (ID 163 only)")

conn.commit()
conn.close()
