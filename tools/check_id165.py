import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
c.execute("SELECT id, result, pnl, account, account_name, mt5_closure_state FROM trades WHERE id = 165")
r = c.fetchone()
if r:
    print(f"ID 165: result={r[1]} pnl={r[2]} account={r[3]} account_name={r[4]} closure={r[5]}")
else:
    print("ID 165 not found")
conn.close()
