import sqlite3, MetaTrader5 as mt5
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT id, ticket, pair, signal, entry, timestamp FROM trades WHERE exit_price IS NULL")
db_open = c.fetchall()
print("DATABASE open trades:")
for t in db_open:
    print(f"  #{t[0]} ticket={t[1]} {t[2]} {t[3]} entry={t[4]}")

mt5.initialize()
# Check Live_Micro
mt5.login(REDACTED_LIVE_ACCOUNT, password='REDACTED_OLD_LIVE_PASSWORD', server='Exness-MT5Real10')
pos = mt5.positions_get()
mt5_tickets = [p.ticket for p in pos] if pos else []

# Check Demo2
mt5.login(REDACTED_DEMO_ACCOUNT, password='REDACTED_DEMO2_PASSWORD', server='Exness-MT5Trial9')
pos2 = mt5.positions_get()
mt5_tickets += [p.ticket for p in pos2] if pos2 else []

print(f"MT5 tickets: {mt5_tickets}")

fixed = 0
for t in db_open:
    if t[1] not in mt5_tickets:
        print(f"STALE: DB ticket {t[1]} - marking closed")
        c.execute("UPDATE trades SET exit_price=?, exit_time=datetime('now'), pnl=0, result='SYNCED' WHERE id=?", (t[4], t[0]))
        fixed += 1

conn.commit()
c.execute("SELECT COUNT(*) FROM trades WHERE exit_price IS NULL")
remaining = c.fetchone()[0]
print(f"\nFixed: {fixed} | DB open: {remaining} | MT5 open: {len(mt5_tickets)}")
print("MATCH!" if remaining == len(mt5_tickets) else "Still mismatched")
conn.close()
mt5.shutdown()
