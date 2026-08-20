import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
c.execute("SELECT id, timestamp, exit_time, result FROM trades WHERE exit_time IS NOT NULL AND timestamp IS NOT NULL AND exit_time < timestamp AND result NOT LIKE 'LEGACY%'")
rows = c.fetchall()
for r in rows:
    print(f"ID {r[0]}: entry={r[1]} exit={r[2]} result={r[3]}")
if not rows:
    print("No bad timestamps found")
conn.close()
