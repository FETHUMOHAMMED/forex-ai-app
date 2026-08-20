import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# ID 163: actual MT5 entry was 1.15542, planned was 1.15123
c.execute("UPDATE trades SET entry = 1.15542, planned_entry = 1.15123 WHERE id = 163")
conn.commit()

c.execute("SELECT id, entry, planned_entry, pnl, result, mt5_position_id FROM trades WHERE id = 163")
r = c.fetchone()
print(f"ID {r[0]}: entry={r[1]} planned={r[2]} pnl={r[3]} result={r[4]} mt5_pos={r[5]}")
conn.close()
print("Fixed ID 163 - entry now reflects actual MT5 execution")
