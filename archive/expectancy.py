import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(AVG(CASE WHEN pnl>0 THEN pnl END),2), ROUND(AVG(CASE WHEN pnl<0 THEN pnl END),2), ROUND(SUM(pnl),2) FROM trades WHERE pnl IS NOT NULL AND pnl != 0 AND strategy_version='V3_REGIME'")
r = c.fetchone()
t, w, avg_win, avg_loss, net = r
if t and t > 0:
    l = t - w
    wr = w/t*100
    ev = (wr/100)*(avg_win or 0) - ((100-wr)/100)*abs(avg_loss or 0)
    print("V3_REGIME: " + str(t) + " trades, " + str(w) + "W/" + str(l) + "L, WR=" + str(round(wr)) + "%")
    print("Avg Win: $" + str(avg_win) + ", Avg Loss: $" + str(avg_loss))
    print("Net PnL: $" + str(net))
    print("Expectancy: $" + str(round(ev,2)) + "/trade")
else:
    print("No V3 trades with PnL yet")

c.execute("SELECT COUNT(*), ROUND(AVG(CASE WHEN pnl>0 THEN pnl END),2), ROUND(AVG(CASE WHEN pnl<0 THEN pnl END),2), ROUND(SUM(pnl),2) FROM trades WHERE pnl IS NOT NULL AND pnl != 0 AND strategy_version='PRE_V3'")
r = c.fetchone()
print("\nPRE_V3: " + str(r[0]) + " trades, Avg Win=$" + str(r[1]) + ", Avg Loss=$" + str(r[2]) + ", Net=$" + str(r[3]))
conn.close()
