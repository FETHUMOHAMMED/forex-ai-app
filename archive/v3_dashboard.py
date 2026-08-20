"""V3-Only Performance Dashboard"""
import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2), ROUND(AVG(CASE WHEN pnl>0 THEN pnl END),2), ROUND(AVG(CASE WHEN pnl<0 THEN pnl END),2) FROM trades WHERE pnl IS NOT NULL AND strategy_version='V3_REGIME'")
r = c.fetchone()
t, w, l, net, avg_w, avg_l = r

print("=" * 50)
print("  V3_REGIME PERFORMANCE")
print("=" * 50)
print("  Trades: " + str(t) + " (" + str(w) + "W / " + str(l) + "L)")
if t > 0:
    print("  Win Rate: " + str(round(w/t*100,1)) + "%")
    print("  Net PnL: $" + str(net))
    print("  Avg Win: $" + str(avg_w))
    print("  Avg Loss: $" + str(avg_l))
    if l > 0 and avg_l:
        pf = (w*avg_w)/(l*abs(avg_l)) if avg_l else 0
        print("  Profit Factor: " + str(round(pf,2)))

c.execute("SELECT COUNT(*) FROM trades WHERE strategy_version='PRE_V3' AND pnl IS NOT NULL")
pre = c.fetchone()[0]
print("\n  PRE_V3 (baseline): " + str(pre) + " trades, -$2039, 27.6% WR")
print("  V3_REGIME: " + str(t) + " trades")
print("=" * 50)
conn.close()
