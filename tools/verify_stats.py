import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT pnl FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL")
pnls = [row[0] for row in c.fetchall()]

print("MANUAL V3 STATS:")
print("Trades: " + str(len(pnls)))
if len(pnls) > 0:
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    wr = len(wins)/len(pnls)*100 if pnls else 0
    print("Wins: " + str(len(wins)) + ", Losses: " + str(len(losses)))
    print("Win Rate: " + str(round(wr,1)) + "%")
    if losses:
        pf = sum(wins)/abs(sum(losses)) if sum(losses) != 0 else 999
        print("Profit Factor: " + str(round(pf,2)))
    print("Net PnL: " + str(round(sum(pnls),2)))
    print("Expectancy: " + str(round(sum(pnls)/len(pnls),2)))

print()
print("DASHBOARD V3 STATS (from API):")
try:
    import urllib.request, json
    resp = urllib.request.urlopen('http://localhost:3001/api/stats', timeout=3)
    data = json.loads(resp.read())
    print("Trades: " + str(data.get('total_trades','N/A')))
    print("Win Rate: " + str(data.get('win_rate','N/A')))
    print("PnL: " + str(data.get('total_pnl','N/A')))
except:
    print("API offline - run dashboard_inst.py instead")

conn.close()
