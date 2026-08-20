import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("""SELECT COUNT(*), 
             SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END),
             SUM(CASE WHEN simulated_result='LOSS' THEN 1 ELSE 0 END),
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN simulated_pnl ELSE 0 END),4),
             ROUND(AVG(CASE WHEN simulated_result='LOSS' THEN simulated_pnl ELSE 0 END),4),
             ROUND(SUM(simulated_pnl),4),
             ROUND(SUM(CASE WHEN simulated_result='WIN' THEN simulated_pnl ELSE 0 END) / 
                   NULLIF(ABS(SUM(CASE WHEN simulated_result='LOSS' THEN simulated_pnl ELSE 0 END)),0), 2),
             ROUND(MIN(simulated_pnl),4),
             ROUND(MAX(simulated_pnl),4)
             FROM shadow_trades WHERE decision='SIMULATED' AND simulated_result!='PENDING'""")
r = c.fetchone()
t, w, l, avg_win, avg_loss, net, pf, worst, best = r
wr = w/t*100 if t else 0
expectancy = net/t if t else 0

print("=" * 55)
print("  PRODUCTION REPLAY METRICS - 291 Trades")
print("=" * 55)
print(f"  Win Rate:      {wr:.1f}% ({w}W / {l}L)")
print(f"  Avg Win:       {avg_win:.4f}")
print(f"  Avg Loss:      {avg_loss:.4f}")
print(f"  Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}" if avg_loss else "  Win/Loss Ratio: N/A")
print(f"  Profit Factor: {pf}")
print(f"  Expectancy:    {expectancy:+.4f}/trade")
print(f"  Net PnL:       {net:+.4f}")
print(f"  Worst Trade:   {worst:.4f}")
print(f"  Best Trade:    {best:.4f}")

# By regime
print(f"\n  By Regime:")
c.execute("""SELECT regime, COUNT(*), 
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1),
             ROUND(SUM(simulated_pnl),4)
             FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL
             GROUP BY regime ORDER BY COUNT(*) DESC""")
for r in c.fetchall():
    print(f"  {r[0]:15s}: {r[1]:3d} trades, {r[2]}% WR, PnL {r[3]:+.4f}")

# By pair
print(f"\n  By Pair:")
c.execute("""SELECT pair, COUNT(*), 
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1),
             ROUND(SUM(simulated_pnl),4)
             FROM shadow_trades WHERE decision='SIMULATED'
             GROUP BY pair ORDER BY COUNT(*) DESC""")
for r in c.fetchall():
    print(f"  {r[0]:10s}: {r[1]:3d} trades, {r[2]}% WR, PnL {r[3]:+.4f}")

print("\n" + "=" * 55)
conn.close()
