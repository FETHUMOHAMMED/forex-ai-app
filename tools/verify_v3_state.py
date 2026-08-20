import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
c.execute("""SELECT id, result, pnl, mt5_closure_state, exit_time 
             FROM trades 
             WHERE strategy_version='V3_REGIME' AND account='Live_Micro' 
             AND result NOT LIKE 'LEGACY%' 
             ORDER BY id""")
for r in c.fetchall():
    exit_str = str(r[4])[:19] if r[4] else 'OPEN'
    print(f"ID {r[0]}: result={r[1]} pnl={r[2]} closure={r[3]} exit={exit_str}")
conn.close()
