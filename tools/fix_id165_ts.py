import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# ID 165: entry is 10:54 local (UTC+3) = 07:54 UTC
# exit is 10:30 UTC
# So entry (07:54 UTC) < exit (10:30 UTC) - CORRECT
# The entry just needs +00:00 timezone marker
c.execute("""
    UPDATE trades SET timestamp = '2026-08-13T07:54:38+00:00' 
    WHERE id = 165
""")
conn.commit()
print("Fixed ID 165 timestamp - entry now UTC with timezone")
print("07:54 UTC (entry) < 10:30 UTC (exit) = CORRECT")
conn.close()
