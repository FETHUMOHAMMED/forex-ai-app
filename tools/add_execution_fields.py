"""Add signal_entry, requested_entry, actual_entry, entry_deviation_pips columns"""
import sqlite3

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# Add missing columns
for col, col_type in [
    ('signal_entry', 'REAL'),
    ('requested_entry', 'REAL'),
    ('actual_entry', 'REAL'),
    ('entry_deviation_pips', 'REAL'),
    ('actual_sl', 'REAL'),
    ('actual_tp', 'REAL'),
]:
    try:
        c.execute(f"ALTER TABLE trades ADD COLUMN {col} {col_type}")
        print(f"Added column: {col}")
    except:
        print(f"Column exists: {col}")

# Backfill ID 163 data
c.execute("""
    UPDATE trades SET 
        signal_entry = planned_entry,
        requested_entry = planned_entry,
        actual_entry = entry,
        actual_sl = stop_loss,
        actual_tp = take_profit
    WHERE id = 163
""")

# Backfill ID 164
c.execute("""
    UPDATE trades SET 
        signal_entry = 1.15542,
        requested_entry = 1.15542,
        actual_entry = entry,
        entry_deviation_pips = 0
    WHERE id = 164
""")

conn.commit()

# Verify
c.execute("""
    SELECT id, signal_entry, requested_entry, actual_entry, entry_deviation_pips
    FROM trades WHERE id IN (163, 164)
""")
for row in c.fetchall():
    print(f"ID {row[0]}: signal={row[1]} requested={row[2]} actual={row[3]} deviation={row[4]} pips")

conn.close()
print("\nDone. Execution fields now separated.")
