import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END), ROUND(AVG(CASE WHEN pnl>0 THEN pnl END),2), ROUND(AVG(CASE WHEN pnl<0 THEN ABS(pnl) END),2), ROUND(SUM(pnl),2) FROM trades WHERE pnl IS NOT NULL")
row = c.fetchone()
total, wins, losses, avg_win, avg_loss, net_pnl = row
wr = wins/total*100 if total else 0
gross_profit = wins * (avg_win or 0)
gross_loss = losses * (avg_loss or 0)
pf = round(gross_profit/gross_loss, 2) if gross_loss > 0 else 0
expectancy = round(net_pnl/total, 2) if total else 0

print("=" * 55)
print(f"  PERFORMANCE REPORT - {total} trades")
print("=" * 55)
print(f"  Win Rate:      {wr:.1f}% ({wins}W / {losses}L)")
print(f"  Avg Win:       ${avg_win}")
print(f"  Avg Loss:      -${avg_loss}")
print(f"  Win/Loss Ratio: {round(avg_win/avg_loss,2) if avg_loss else 0}:1")
print(f"  Net PnL:       ${net_pnl}")
print(f"  Profit Factor: {pf}")
print(f"  Expectancy:    ${expectancy}/trade")

print(f"\n  --- CLEAN EXPERIMENT (EURUSD + GBPUSD) ---")
c.execute("SELECT pair, COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2), ROUND(AVG(CASE WHEN pnl>0 THEN pnl END),2), ROUND(AVG(CASE WHEN pnl<0 THEN ABS(pnl) END),2) FROM trades WHERE pnl IS NOT NULL AND pair IN ('EURUSD','GBPUSD') GROUP BY pair")
clean_wins = 0
clean_total = 0
clean_pnl = 0
for r in c.fetchall():
    pair, cnt, w, pnl, aw, al = r
    wr2 = w/cnt*100 if cnt else 0
    clean_wins += w
    clean_total += cnt
    clean_pnl += pnl
    print(f"  {pair:10s}: {cnt:2d} trades, {wr2:.0f}% WR, PnL ${pnl}, avg win ${aw}, avg loss -${al}")

clean_wr = clean_wins/clean_total*100 if clean_total else 0
print(f"  {'COMBINED':10s}: {clean_total:2d} trades, {clean_wr:.0f}% WR, PnL ${clean_pnl}")

print(f"\n  --- OLD LOSERS (BLOCKED) ---")
c.execute("SELECT pair, COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2) FROM trades WHERE pnl IS NOT NULL AND pair NOT IN ('EURUSD','GBPUSD') GROUP BY pair ORDER BY SUM(pnl) ASC")
for r in c.fetchall():
    pair, cnt, w, pnl = r
    wr3 = w/cnt*100 if cnt else 0
    print(f"  {pair:10s}: {cnt:2d} trades, {wr3:.0f}% WR, PnL ${pnl}")

print(f"\n  Last 10 trades:")
c.execute("SELECT pair, signal, ROUND(pnl,2), result FROM trades WHERE pnl IS NOT NULL ORDER BY id DESC LIMIT 10")
for r in c.fetchall():
    print(f"  {r[0]} {r[1]} ${r[2]:+7.2f} {r[3]}")

print("=" * 55)
conn.close()
