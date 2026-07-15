import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# Add research tag columns
try:
    c.execute('ALTER TABLE trades ADD COLUMN trade_mode TEXT DEFAULT "PRODUCTION"')
except: pass
try:
    c.execute('ALTER TABLE trades ADD COLUMN filter_version TEXT')
except: pass
try:
    c.execute('ALTER TABLE shadow_trades ADD COLUMN trade_mode TEXT DEFAULT "SHADOW"')
except: pass
try:
    c.execute('ALTER TABLE research_decisions ADD COLUMN trade_mode TEXT DEFAULT "RESEARCH"')
except: pass

conn.commit()

# Tag existing data
c.execute("UPDATE trades SET trade_mode='PRODUCTION', filter_version='V1-V8'")
c.execute("UPDATE shadow_trades SET trade_mode='SHADOW'")
c.execute("UPDATE research_decisions SET trade_mode='RESEARCH'")
conn.commit()

# Verify
c.execute("SELECT trade_mode, COUNT(*) FROM trades GROUP BY trade_mode")
print("Trades by mode:")
for row in c.fetchall():
    print("  " + str(row[0]) + ": " + str(row[1]))

c.execute("SELECT trade_mode, COUNT(*) FROM shadow_trades GROUP BY trade_mode")
print("Shadow by mode:")
for row in c.fetchall():
    print("  " + str(row[0]) + ": " + str(row[1]))

c.execute("SELECT trade_mode, COUNT(*) FROM research_decisions GROUP BY trade_mode")
print("Research by mode:")
for row in c.fetchall():
    print("  " + str(row[0]) + ": " + str(row[1]))

conn.close()
print("\nAll data tagged: PRODUCTION / SHADOW / RESEARCH")
