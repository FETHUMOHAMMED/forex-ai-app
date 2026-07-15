import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 55)
print("  EDGE ANALYSIS - 2,207 Data Points")
print("=" * 55)

# 1. EXPECTANCY BY PAIR
print("\n1. EXPECTANCY BY PAIR (shadow trades)")
c.execute("""SELECT pair, COUNT(*), 
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1),
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN simulated_pnl ELSE 0 END),2),
             ROUND(AVG(CASE WHEN simulated_result='LOSS' THEN simulated_pnl ELSE 0 END),2)
             FROM shadow_trades WHERE decision='SIMULATED' AND simulated_result!='PENDING'
             GROUP BY pair HAVING COUNT(*)>=20 ORDER BY COUNT(*) DESC""")
for r in c.fetchall():
    pair, cnt, wr, avg_win, avg_loss = r
    expectancy = (wr/100)*avg_win - ((100-wr)/100)*abs(avg_loss) if avg_loss else 0
    print(f"  {pair:10s}: {cnt:3d} trades, {wr}% WR, win={avg_win}, loss={avg_loss}, expect={expectancy:+.2f}")

# 2. EXPECTANCY BY REGIME
print("\n2. EXPECTANCY BY REGIME")
c.execute("""SELECT regime, COUNT(*),
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1)
             FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL
             GROUP BY regime HAVING COUNT(*)>=5 ORDER BY COUNT(*) DESC""")
for r in c.fetchall():
    print(f"  {r[0]:15s}: {r[1]:3d} trades, {r[2]}% WR")

# 3. EXPECTANCY BY CONFIDENCE BUCKET
print("\n3. EXPECTANCY BY CONFIDENCE BUCKET")
buckets = [(0.48,0.50),(0.50,0.53),(0.53,0.56),(0.56,0.60),(0.60,0.70)]
for lo, hi in buckets:
    c.execute("""SELECT COUNT(*),
                 ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1)
                 FROM shadow_trades WHERE decision='SIMULATED'
                 AND confidence >= ? AND confidence < ?""", (lo, hi))
    row = c.fetchone()
    if row[0] > 0:
        print(f"  {lo:.2f}-{hi:.2f}: {row[0]:3d} trades, {row[1]}% WR")

# 4. BEST COMBINATIONS
print("\n4. BEST PAIR + REGIME COMBOS (min 15 trades)")
c.execute("""SELECT pair, regime, COUNT(*),
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1)
             FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL
             GROUP BY pair, regime HAVING COUNT(*)>=15 ORDER BY AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) DESC""")
for r in c.fetchall():
    star = " ***TOP EDGE***" if r[3] >= 55 else ""
    print(f"  {r[0]:8s} + {r[1]:12s}: {r[2]:3d} trades, {r[3]}% WR{star}")

# 5. REAL TRADES BY PAIR
print("\n5. REAL TRADES (63 total)")
c.execute("""SELECT pair, COUNT(*),
             ROUND(AVG(CASE WHEN pnl>0 THEN 1 ELSE 0 END)*100,1),
             ROUND(SUM(pnl),2)
             FROM trades WHERE pnl IS NOT NULL
             GROUP BY pair ORDER BY COUNT(*) DESC""")
for r in c.fetchall():
    print(f"  {r[0]:10s}: {r[1]:2d} trades, {r[2]}% WR, PnL ${r[3]}")

# 6. RECOMMENDATIONS
print("\n6. RECOMMENDED FOCUS PAIRS")
c.execute("""SELECT pair, COUNT(*),
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1)
             FROM shadow_trades WHERE decision='SIMULATED'
             GROUP BY pair HAVING COUNT(*)>=30
             ORDER BY AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) DESC LIMIT 5""")
top = c.fetchall()
for r in top:
    print(f"  {r[0]}: {r[1]} trades, {r[2]}% WR")

print("\n" + "=" * 55)
conn.close()
