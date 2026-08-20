import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
c.execute("""SELECT id, timestamp, exit_time, result 
             FROM trades 
             WHERE exit_time IS NOT NULL AND timestamp IS NOT NULL 
             AND exit_time < timestamp AND result NOT LIKE 'LEGACY%'""")
for r in c.fetchall():
    print(f"ID {r[0]}: entry={r[1]} exit={r[2]} result={r[3]}")
conn.close()
