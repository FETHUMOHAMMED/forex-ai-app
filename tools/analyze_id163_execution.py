"""P0: Analyze ID 163 execution contract - Is the SL valid for the actual fill?"""
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT * FROM trades WHERE id = 163")
row = c.fetchone()
cols = [d[0] for d in c.description]
t = dict(zip(cols, row))

print("=" * 70)
print("  P0: ID 163 EXECUTION CONTRACT ANALYSIS")
print("=" * 70)

# Signal plan
print("\n  SIGNAL PLAN:")
print(f"    Planned Entry: {t['planned_entry']}")
print(f"    Planned SL:    {t['planned_sl']}")
print(f"    Planned TP:    {t['planned_tp']}")
print(f"    Direction:     {t['signal']}")

# Actual execution
print("\n  ACTUAL EXECUTION (from DB):")
print(f"    DB Entry:      {t['entry']}")
print(f"    DB Exit:       {t['exit_price']}")
print(f"    DB Volume:     {t['volume']}")
print(f"    DB PnL:        {t['pnl']}")

# Get actual MT5 fill from deals
mt5.initialize()
deals = mt5.history_deals_get(
    datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc),
    datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
    position=589584400
)

if deals:
    print("\n  MT5 DEALS FOR POSITION 589584400:")
    for d in deals:
        if d.position_id == 589584400:
            action = "OPEN" if d.entry == 0 else "CLOSE"
            print(f"    Deal {d.ticket}: {action} @ {d.price} | Vol: {d.volume} | Profit: {d.profit}")
else:
    print("\n  No MT5 deals found")

mt5.shutdown()

# === THE CRITICAL CHECK ===
direction = t['signal']  # SELL
actual_entry = t['entry']  # 1.15542
actual_sl = t['stop_loss']  # 1.15299
actual_tp = t['take_profit']  # 1.14842

print(f"\n  EXECUTION CONTRACT CHECK:")
print(f"    Direction: {direction}")
print(f"    Actual Entry: {actual_entry}")
print(f"    Actual SL:    {actual_sl}")
print(f"    Actual TP:    {actual_tp}")

if direction == 'SELL':
    expected_order = f"TP ({actual_tp}) < Entry ({actual_entry}) < SL ({actual_sl})"
    tp_ok = actual_tp < actual_entry
    sl_ok = actual_sl > actual_entry
    actual_order = f"TP={actual_tp} < Entry={actual_entry} = {tp_ok}, Entry={actual_entry} < SL={actual_sl} = {sl_ok}"
elif direction == 'BUY':
    expected_order = f"SL ({actual_sl}) < Entry ({actual_entry}) < TP ({actual_tp})"
    tp_ok = actual_tp > actual_entry
    sl_ok = actual_sl < actual_entry
    actual_order = f"SL={actual_sl} < Entry={actual_entry} = {sl_ok}, Entry={actual_entry} < TP={actual_tp} = {tp_ok}"

print(f"\n    Expected: {expected_order}")
print(f"    Actual:   {actual_order}")

if not sl_ok:
    print(f"\n  VERDICT: EXECUTION CONTRACT VIOLATED")
    print(f"  SL ({actual_sl}) is BELOW entry ({actual_entry}) for a SELL")
    print(f"  This means the SL would trigger IMMEDIATELY at open")
    print(f"  The stop is on the WRONG SIDE of the entry price")
    print(f"  This trade should NOT count as clean execution integrity")
elif not tp_ok:
    print(f"\n  VERDICT: EXECUTION CONTRACT VIOLATED")
    print(f"  TP is on the wrong side of entry")
else:
    print(f"\n  VERDICT: EXECUTION CONTRACT VALID")

# Entry deviation
planned = t['planned_entry']
deviation_pips = abs(actual_entry - planned) * 10000
print(f"\n  ENTRY DEVIATION:")
print(f"    Planned: {planned}")
print(f"    Actual:  {actual_entry}")
print(f"    Deviation: {deviation_pips:.1f} pips")
print(f"    Status: {'EXTREME - investigation required' if deviation_pips > 5 else 'Acceptable'}")

conn.close()
