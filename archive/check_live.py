import sqlite3, MetaTrader5 as mt5

conn = sqlite3.connect("ai-service/trades.db")
c = conn.cursor()

c.execute("SELECT account_name, COUNT(*) FROM trades WHERE pnl IS NOT NULL GROUP BY account_name")
print("Trades by account:")
for row in c.fetchall():
    print("  " + str(row[0]) + ": " + str(row[1]))

# Check MT5 for live account positions
mt5.initialize()
# Try login to live account
result = mt5.login(REDACTED_LIVE_ACCOUNT, password="REDACTED_OLD_LIVE_PASSWORD", server="Exness-MT5Trial9")
print("\nLive account login: " + ("OK" if result else "FAILED"))
if result:
    info = mt5.account_info()
    if info:
        print("Balance: " + str(info.balance))
        positions = mt5.positions_get()
        print("Open positions: " + str(len(positions) if positions else 0))
        if positions:
            for p in positions:
                print("  " + p.symbol + " " + ("BUY" if p.type==0 else "SELL") + " PnL=" + str(round(p.profit,2)))

# Switch back to Demo2
mt5.login(REDACTED_DEMO_ACCOUNT, password="REDACTED_DEMO2_PASSWORD", server="Exness-MT5Trial9")
mt5.shutdown()
conn.close()
