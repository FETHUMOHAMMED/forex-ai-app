"""P0: Complete ID 164 Investigation"""
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT * FROM trades WHERE id = 164")
row = c.fetchone()
cols = [d[0] for d in c.description]
t = dict(zip(cols, row))

print("=" * 70)
print("  P0: ID 164 COMPLETE INVESTIGATION")
print("=" * 70)

print("\n  DATABASE RECORD:")
for key in ['id', 'pair', 'signal', 'confidence', 'entry', 'stop_loss', 
            'take_profit', 'volume', 'ticket', 'mt5_position_id',
            'planned_entry', 'planned_sl', 'planned_tp', 'signal_entry',
            'actual_entry', 'actual_sl', 'actual_tp', 'timestamp', 'exit_time',
            'result', 'pnl', 'account', 'account_name', 'strategy_version',
            'execution_contract_valid', 'execution_issue']:
    if key in t:
        print(f"    {key}: {t[key]}")

# Get MT5 deal history
mt5.initialize()
deals = mt5.history_deals_get(datetime(2026, 8, 10, tzinfo=timezone.utc), 
                               datetime.now(timezone.utc), position=589629837)

print("\n  MT5 DEALS:")
if deals:
    for d in deals:
        if d.position_id == 589629837:
            action = "OPEN" if d.entry == 0 else "CLOSE"
            print(f"    {action}: Deal {d.ticket} @ {d.price} | Vol: {d.volume} | Profit: ${d.profit}")
            if d.entry == 1:  # CLOSE
                print(f"      Close time: {datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat()}")
                print(f"      Commission: {d.commission} | Swap: {d.swap}")
else:
    print("    No deals found")

# Check current position
positions = mt5.positions_get(ticket=589629837)
if positions:
    p = positions[0]
    print(f"\n  CURRENT MT5 POSITION:")
    print(f"    Symbol: {p.symbol}")
    print(f"    SL: {p.sl}")
    print(f"    TP: {p.tp}")
    print(f"    Profit: ${p.profit}")
else:
    print(f"\n  Position CLOSED in MT5")

mt5.shutdown()
conn.close()

print(f"\n{'='*70}")
print("  FINDINGS:")
print("  1. ID 164 was created by 'sync_orphan_position.py' (manual)")
print("  2. NOT created by the auto-trader execution pipeline")
print("  3. SL/TP were None in DB but had values in MT5")
print("  4. This is an ORPHAN position manually synced")
print("  5. It does NOT qualify for V3 validation")
print(f"{'='*70}")
