import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# Fix ID 163
c.execute("UPDATE trades SET result='LOSS', reason='closed' WHERE id=163 AND result LIKE 'LEGACY%'")
c.execute("SELECT id, account, account_name, result FROM trades WHERE id=163")
r = c.fetchone()
print(f"ID 163: account={r[1]} account_name={r[2]} result={r[3]}")

# Clean stats
c.execute("SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%'")
total_clean = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND strategy_version='V3_REGIME' AND account='Live_Micro'")
v3_clean = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM trades WHERE result LIKE 'LEGACY%'")
legacy = c.fetchone()[0]

print(f"Clean records: {total_clean}")
print(f"Clean V3 Live_Micro: {v3_clean}")
print(f"Legacy-invalid (preserved): {legacy}")
print(f"Total: {total_clean + legacy}")

conn.commit()
conn.close()
