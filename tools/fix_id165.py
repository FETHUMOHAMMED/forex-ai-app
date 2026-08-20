import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# ID 165: account=None, account_name=Demo2 - should be Live_Micro
# The position was on Live_Micro (ticket 591215040 was in Live_Micro account)
c.execute("""
    UPDATE trades SET 
        account = 'Live_Micro',
        account_name = 'Live_Micro',
        account_id = REDACTED_LIVE_ACCOUNT,
        environment = 'LIVE_MICRO_VALIDATION'
    WHERE id = 165
""")
conn.commit()
print("ID 165: account corrected to Live_Micro")

# Verify
c.execute("SELECT id, account, account_name, account_id, result, pnl FROM trades WHERE id = 165")
r = c.fetchone()
print(f"  ID {r[0]}: account={r[1]} name={r[2]} id={r[3]} result={r[4]} pnl={r[5]}")
conn.close()
