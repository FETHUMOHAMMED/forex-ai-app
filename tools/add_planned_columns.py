import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# Add new columns
for col, col_type in [
    ('planned_entry', 'REAL'),
    ('planned_sl', 'REAL'),
    ('planned_tp', 'REAL'),
    ('mt5_position_id', 'INTEGER')
]:
    try:
        c.execute(f"ALTER TABLE trades ADD COLUMN {col} {col_type}")
        print(f"Added column: {col}")
    except:
        print(f"Column already exists: {col}")

# Backfill: for existing trades, planned = entry (since we stored planned as entry)
c.execute("UPDATE trades SET planned_entry = entry WHERE planned_entry IS NULL")
c.execute("UPDATE trades SET planned_sl = stop_loss WHERE planned_sl IS NULL")
c.execute("UPDATE trades SET planned_tp = take_profit WHERE planned_tp IS NULL")
c.execute("UPDATE trades SET mt5_position_id = ticket WHERE mt5_position_id IS NULL")

conn.commit()

# Verify
print("\nSchema now:")
cols = c.execute("PRAGMA table_info(trades)").fetchall()
for col in cols:
    if col[1] in ('planned_entry', 'planned_sl', 'planned_tp', 'mt5_position_id', 'entry', 'stop_loss'):
        print(f"  {col[1]}")

conn.close()
print("\nDone. Future trades will capture both planned and actual prices.")
