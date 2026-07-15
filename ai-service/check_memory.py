import sqlite3
conn = sqlite3.connect('trades.db')
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM trade_memory')
tm = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM performance_memory')
pm = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL')
closed = c.fetchone()[0]

print('trade_memory: ' + str(tm))
print('performance_memory: ' + str(pm))
print('closed trades: ' + str(closed))
print('gap: ' + str(closed - tm))

# Check memory table schema
c.execute('PRAGMA table_info(trade_memory)')
cols = c.fetchall()
print('\ntrade_memory columns:')
for col in cols:
    print('  ' + col[1] + ' ' + col[2])

c.execute('SELECT * FROM trade_memory LIMIT 1')
row = c.fetchone()
if row:
    print('\nSample row: ' + str(row))

conn.close()
