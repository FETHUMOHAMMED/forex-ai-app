"""Full audit trail for ID 164 - the current open V3 position"""
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
print("  ID 164 - FULL EXECUTION AUDIT TRAIL")
print("=" * 70)

# Signal metadata
print("\n  SIGNAL:")
print(f"    Pair: {t['pair']} {t['signal']}")
print(f"    Confidence: {t['confidence']}")
print(f"    Planned Entry: {t.get('planned_entry')}")
print(f"    Planned SL: {t.get('planned_sl')}")
print(f"    Planned TP: {t.get('planned_tp')}")
print(f"    Timestamp: {t['timestamp']}")

# Actual execution
print("\n  EXECUTION:")
print(f"    Entry: {t['entry']}")
print(f"    SL: {t['stop_loss']}")
print(f"    TP: {t['take_profit']}")
print(f"    Volume: {t['volume']}")
print(f"    Ticket: {t['ticket']}")
print(f"    MT5 Position ID: {t.get('mt5_position_id')}")

# Get MT5 position details
mt5.initialize()
positions = mt5.positions_get(ticket=589629837)
if positions:
    p = positions[0]
    print(f"\n  MT5 POSITION:")
    print(f"    Symbol: {p.symbol}")
    print(f"    Direction: {'SELL' if p.type == 1 else 'BUY'}")
    print(f"    Volume: {p.volume}")
    print(f"    Open Price: {p.price_open}")
    print(f"    Current Price: {p.price_current}")
    print(f"    SL: {p.sl}")
    print(f"    TP: {p.tp}")
    print(f"    Profit: ${p.profit:.2f}")
    
    # Execution contract check
    direction = 'SELL' if p.type == 1 else 'BUY'
    actual_entry = p.price_open
    actual_sl = p.sl
    actual_tp = p.tp
    
    print(f"\n  EXECUTION CONTRACT:")
    if direction == 'SELL':
        sl_valid = actual_sl > actual_entry if actual_sl else False
        tp_valid = actual_tp < actual_entry if actual_tp else False
        print(f"    SL ({actual_sl}) > Entry ({actual_entry}): {sl_valid}")
        print(f"    TP ({actual_tp}) < Entry ({actual_entry}): {tp_valid}")
    else:
        sl_valid = actual_sl < actual_entry if actual_sl else False
        tp_valid = actual_tp > actual_entry if actual_tp else False
        print(f"    SL ({actual_sl}) < Entry ({actual_entry}): {sl_valid}")
        print(f"    TP ({actual_tp}) > Entry ({actual_entry}): {tp_valid}")
    
    # Deviation from planned
    planned = t.get('planned_entry')
    if planned:
        deviation = abs(actual_entry - planned) * 10000
        print(f"\n    Planned: {planned}")
        print(f"    Actual: {actual_entry}")
        print(f"    Deviation: {deviation:.1f} pips")
        print(f"    {'PASS' if deviation <= 5 else 'FAIL - EXTREME'}")
    
    # SL/TP set?
    print(f"\n  SL/TP STATUS:")
    print(f"    SL set: {actual_sl != 0 if actual_sl else False}")
    print(f"    TP set: {actual_tp != 0 if actual_tp else False}")
else:
    print("\n  POSITION NOT FOUND IN MT5 - may have closed")

mt5.shutdown()
conn.close()

print(f"\n{'='*70}")
print("  VERDICT:")
print("  ID 164 is OPEN - do NOT count toward validation")
print("  Must pass execution contract when it closes")
print(f"{'='*70}")
