import sqlite3
conn = sqlite3.connect("ai-service/trades.db")
try:
    conn.execute("ALTER TABLE trades ADD COLUMN account_name TEXT DEFAULT 'Demo2'")
    print("Added account_name column")
except:
    print("Column already exists")
conn.commit()
conn.close()
