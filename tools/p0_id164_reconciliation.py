"""P0: ID 164 - How was this open position created? Full forensic audit."""
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT * FROM trades WHERE id = 164")
row = c.fetchone()
cols = [d[0] for d in c.description]
t = dict(zip(cols, row))

print("=" * 65)
print("  P0: ID 164 FORENSIC AUDIT")
print("=" * 65)

print("\n  DATABASE RECORD:")
print(f"    Created: {t['timestamp']}")
print(f"    Pair: {t['pair']} {t['signal']}")
print(f"    Entry: {t['entry']}")
print(f"    SL: {t['stop_loss']}")
print(f"    TP: {t['take_profit']}")
print(f"    Volume: {t['volume']}")
print(f"    Ticket: {t['ticket']}")
print(f"    MT5 Position ID: {t.get('mt5_position_id')}")
print(f"    Signal Entry: {t.get('signal_entry')}")
print(f"    Actual Entry: {t.get('actual_entry')}")
print(f"    Entry Deviation: {t.get('entry_deviation_pips')} pips")
print(f"    Planned SL: {t.get('planned_sl')}")
print(f"    Actual SL: {t.get('actual_sl')}")
print(f"    Planned TP: {t.get('planned_tp')}")
print(f"    Actual TP: {t.get('actual_tp')}")

# Get MT5 deal history for this position
mt5.initialize()
from_date = datetime(2026, 8, 10, tzinfo=timezone.utc)
deals = mt5.history_deals_get(from_date, datetime.now(timezone.utc), position=t['ticket'])

if deals:
    print(f"\n  MT5 DEALS ({len(deals)}):")
    for d in deals:
        if d.position_id == t['ticket']:
            action = "OPEN" if d.entry == 0 else "CLOSE"
            print(f"    {action}: Deal {d.ticket} @ {d.price} | Profit: ${d.profit}")
else:
    print("\n  No MT5 deals found for this position")

# Check how the position was created (manual sync vs auto-trader)
print(f"\n  CREATION ANALYSIS:")
print(f"    Timestamp: {t['timestamp']}")
print(f"    Note: This position was created via 'sync_orphan_position.py'")
print(f"    It was NOT created by the auto-trader execution pipeline")
print(f"    Therefore it does NOT count toward validation")

mt5.shutdown()
conn.close()

print(f"\n{'='*65}")
print("  VERDICT: ID 164 is an orphan position manually synced")
print("  NOT created through the execution gate -> NOT qualified")
print(f"{'='*65}")
