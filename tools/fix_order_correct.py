import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

# STEP 1: Add column FIRST
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
try:
    c.execute("ALTER TABLE trades ADD COLUMN mt5_closure_state TEXT")
    print("Added mt5_closure_state column")
except:
    print("Column already exists")

# Add other risk columns
risk_columns = [
    ('equity_at_signal', 'REAL'), ('equity_at_order', 'REAL'),
    ('risk_percent', 'REAL'), ('risk_budget', 'REAL'),
    ('entry_at_order', 'REAL'), ('sl_at_order', 'REAL'),
    ('tp_at_order', 'REAL'), ('volume_requested', 'REAL'),
    ('volume_executed', 'REAL'), ('estimated_risk', 'REAL'),
    ('actual_risk', 'REAL'), ('pip_value', 'REAL'),
    ('contract_size', 'REAL'),
]
for col, col_type in risk_columns:
    try:
        c.execute(f"ALTER TABLE trades ADD COLUMN {col} {col_type}")
    except:
        pass
conn.commit()
print("All columns ready")

# STEP 2: Get MT5 closure state
def get_mt5_state(pos_ticket):
    mt5.initialize()
    positions = mt5.positions_get(ticket=pos_ticket)
    if positions:
        mt5.shutdown()
        return "OPEN"
    deals = mt5.history_deals_get(datetime(2026, 8, 1, tzinfo=timezone.utc), 
                                   datetime.now(timezone.utc), position=pos_ticket)
    if deals:
        for d in deals:
            if d.position_id == pos_ticket and d.entry == 1:
                mt5.shutdown()
                return "CLOSED"
    mt5.shutdown()
    return "UNKNOWN"

# STEP 3: Backfill
c.execute("SELECT id, mt5_position_id FROM trades WHERE mt5_position_id IS NOT NULL")
for trade_id, pos_ticket in c.fetchall():
    state = get_mt5_state(pos_ticket)
    c.execute("UPDATE trades SET mt5_closure_state = ? WHERE id = ?", (state, trade_id))
    print(f"  ID {trade_id}: {state}")

conn.commit()
conn.close()
print("Done")
