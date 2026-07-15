import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END), ROUND(AVG(CASE WHEN pnl>0 THEN pnl END),2), ROUND(AVG(CASE WHEN pnl<0 THEN pnl END),2), ROUND(SUM(pnl),2), ROUND(SUM(CASE WHEN pnl>0 THEN pnl END)/NULLIF(ABS(SUM(CASE WHEN pnl<0 THEN pnl END)),0),2) FROM trades WHERE pnl IS NOT NULL AND pnl != 0")
row = c.fetchone()
total, wins, losses, avg_win, avg_loss, net_pnl, pf = row
wr = wins/total*100 if total else 0
print("=" * 50)
print("  PERFORMANCE REPORT - " + str(total) + " trades")
print("=" * 50)
print(f"  Win Rate:     {wr:.1f}% ({wins}W / {losses}L)")
print(f"  Avg Win:      ${avg_win}")
print(f"  Avg Loss:     ${avg_loss}")
print(f"  Net PnL:      ${net_pnl}")
print(f"  Profit Factor: {pf}")
print(f"  Expectancy:   ${round(net_pnl/total,2)}/trade")

print("\n  By Pair:")
c.execute("SELECT pair, COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2) FROM trades WHERE pnl IS NOT NULL AND pnl != 0 GROUP BY pair ORDER BY COUNT(*) DESC")
for r in c.fetchall():
    wr2 = r[2]/r[1]*100 if r[1] else 0
    print(f"  {r[0]:10s}: {r[1]:3d} trades, {wr2:.0f}% WR, PnL ${r[3]}")

print("\n  Last 10 trades:")
c.execute("SELECT pair, signal, ROUND(pnl,2), result, exit_time FROM trades WHERE pnl IS NOT NULL AND pnl != 0 ORDER BY id DESC LIMIT 10")
for r in c.fetchall():
    print(f"  {r[0]} {r[1]} ${r[2]:+6.2f} {r[3]}")

print("\n  TARGET: 100 trades (need " + str(100-total) + " more)")
print("=" * 50)
conn.close()
