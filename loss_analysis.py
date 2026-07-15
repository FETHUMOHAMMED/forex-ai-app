import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 60)
print("  LOSS ANALYSIS - Why trades fail")
print("=" * 60)

c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL AND pnl < 0")
total_losses = c.fetchone()[0]
c.execute("SELECT ROUND(SUM(pnl),2), ROUND(AVG(pnl),2), ROUND(MIN(pnl),2), ROUND(MAX(pnl),2) FROM trades WHERE pnl < 0")
sum_loss, avg_loss, max_loss, min_loss = c.fetchone()
print(f"\nTotal losses: {total_losses}")
print(f"Sum: ${sum_loss} | Avg: ${avg_loss} | Worst: ${max_loss} | Best loss: ${min_loss}")

print("\n--- By Pair ---")
c.execute("SELECT pair, COUNT(*), ROUND(AVG(pnl),2), ROUND(MIN(pnl),2) FROM trades WHERE pnl < 0 GROUP BY pair ORDER BY COUNT(*) DESC")
for r in c.fetchall():
    print(f"  {r[0]:10s}: {r[1]:2d} losses, avg ${r[2]}, worst ${r[3]}")

print("\n--- By Direction ---")
c.execute("SELECT signal, COUNT(*), ROUND(AVG(pnl),2) FROM trades WHERE pnl < 0 GROUP BY signal")
for r in c.fetchall():
    print(f"  {r[0]:6s}: {r[1]:2d} losses, avg ${r[2]}")

print("\n--- Worst 10 Losses ---")
c.execute("SELECT pair, signal, ROUND(pnl,2), institutional_bias, dealer_pressure, liquidity_state, institutional_score FROM trades WHERE pnl < 0 ORDER BY pnl ASC LIMIT 10")
for r in c.fetchall():
    print(f"  {r[0]} {r[1]} ${r[2]:+7.2f} | bias={r[3]} dealer={r[4]} liq={r[5]} score={r[6]}")

print("\n--- Losses by Dealer Pressure ---")
c.execute("SELECT dealer_pressure, COUNT(*), ROUND(AVG(pnl),2) FROM trades WHERE pnl < 0 AND dealer_pressure IS NOT NULL GROUP BY dealer_pressure")
for r in c.fetchall():
    print(f"  {r[0]:20s}: {r[1]:2d} losses, avg ${r[2]}")

print("\n--- Large Losses (>$100) ---")
c.execute("SELECT pair, signal, ROUND(pnl,2), institutional_bias, liquidity_state, dealer_pressure FROM trades WHERE pnl < -100 ORDER BY pnl ASC")
large = c.fetchall()
if large:
    for r in large:
        print(f"  {r[0]} {r[1]} ${r[2]} | bias={r[3]} liq={r[4]} dealer={r[5]}")
else:
    print("  None! All losses under $100")

print("\n" + "=" * 60)
conn.close()
