import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 65)
print("  COMPLETE DATA ANALYSIS - 120+ DATA POINTS")
print("=" * 65)

c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
real = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM shadow_trades")
shadow = c.fetchone()[0]
total = real + shadow
print("\n1. DATA VOLUME")
print("   Real trades: " + str(real))
print("   Shadow trades: " + str(shadow))
print("   COMBINED: " + str(total) + (" >= 120 TARGET REACHED!" if total >= 120 else " (need " + str(120-total) + " more)"))

print("\n2. REGIME PERFORMANCE")
c.execute("SELECT regime, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END), ROUND(AVG(confidence), 3) FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL GROUP BY regime ORDER BY COUNT(*) DESC")
for row in c.fetchall():
    wr = row[2]/row[1]*100 if row[1] > 0 else 0
    bar = "#" * int(wr/5)
    print("   " + str(row[0]) + ": " + str(row[1]) + " trades, " + str(round(wr)) + "% WR " + bar)
    print("     Avg confidence: " + str(row[3]))

print("\n3. PAIR RANKING")
c.execute("SELECT pair, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END), ROUND(AVG(confidence), 3), ROUND(AVG(opportunity_score), 1) FROM shadow_trades WHERE decision='SIMULATED' GROUP BY pair ORDER BY COUNT(*) DESC")
print("   Pair         Trades   WR      AvgConf  AvgScore  Rec")
print("   " + "-" * 58)
for row in c.fetchall():
    wr = row[2]/row[1]*100 if row[1] > 0 else 0
    rec = "KEEP" if wr >= 40 else "WATCH" if wr >= 30 else "DROP"
    print("   " + str(row[0]).ljust(13) + str(row[1]).ljust(9) + str(round(wr)).ljust(7) + str(row[3]).ljust(9) + str(row[4]).ljust(10) + rec)

print("\n4. BEST REGIME x PAIR (min 5 trades)")
c.execute("SELECT regime, pair, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL GROUP BY regime, pair HAVING COUNT(*) >= 5 ORDER BY COUNT(*) DESC")
for row in c.fetchall():
    wr = row[3]/row[2]*100 if row[2] > 0 else 0
    star = " ***HIGH WIN***" if wr >= 60 else ""
    print("   " + str(row[0]).ljust(15) + str(row[1]).ljust(10) + str(row[2]) + " trades, " + str(round(wr)) + "% WR" + star)

print("\n5. CONFIDENCE vs WIN RATE")
brackets = [(0.50, 0.53), (0.53, 0.56), (0.56, 0.60), (0.60, 0.70)]
for lo, hi in brackets:
    c.execute("SELECT COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) FROM shadow_trades WHERE decision='SIMULATED' AND confidence >= ? AND confidence < ?", (lo, hi))
    row = c.fetchone()
    if row[0] > 0:
        wr = row[1]/row[0]*100
        print("   Conf " + str(lo) + "-" + str(hi) + ": " + str(row[0]) + " trades, " + str(round(wr)) + "% WR")

print("\n6. GRADE vs WIN RATE")
c.execute("SELECT grade, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) FROM shadow_trades WHERE decision='SIMULATED' AND grade IS NOT NULL GROUP BY grade ORDER BY grade")
for row in c.fetchall():
    wr = row[2]/row[1]*100 if row[1] > 0 else 0
    print("   Grade " + str(row[0]) + ": " + str(row[1]) + " trades, " + str(round(wr)) + "% WR")

print("\n7. RECOMMENDATIONS FOR VOLUME 9")
print("   Based on " + str(total) + " data points:")
print()

c.execute("SELECT regime, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL GROUP BY regime ORDER BY COUNT(*) DESC")
regimes = c.fetchall()
if regimes:
    best = max(regimes, key=lambda r: r[2]/r[1]*100 if r[1] > 0 else 0)
    wr = best[2]/best[1]*100 if best[1] > 0 else 0
    print("   1. Best regime: " + str(best[0]) + " (" + str(round(wr)) + "% WR)")
    worst = min(regimes, key=lambda r: r[2]/r[1]*100 if r[1] > 0 else 100)
    wr_w = worst[2]/worst[1]*100 if worst[1] > 0 else 0
    print("   2. Avoid regime: " + str(worst[0]) + " (" + str(round(wr_w)) + "% WR)")

c.execute("SELECT pair, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) FROM shadow_trades WHERE decision='SIMULATED' GROUP BY pair HAVING COUNT(*) >= 5")
pairs = c.fetchall()
if pairs:
    sorted_pairs = sorted(pairs, key=lambda r: r[2]/r[1]*100 if r[1] > 0 else 0, reverse=True)
    best_p = sorted_pairs[0]
    wr = best_p[2]/best_p[1]*100 if best_p[1] > 0 else 0
    print("   3. Best pair: " + str(best_p[0]) + " (" + str(round(wr)) + "% WR)")
    drops = [p for p in sorted_pairs if (p[2]/p[1]*100 if p[1] > 0 else 0) < 35]
    if drops:
        d = ", ".join([p[0] for p in drops])
        print("   4. Drop candidates: " + d)

print("   5. Session: London + Asian only (NY/Overlap blocked)")
print("   6. Grade filter: Only Grade C+ trades")

print("\n" + "=" * 65)
print("  ANALYSIS COMPLETE")
print("  DATA: " + str(total) + " points")
print("  VOLUME 9: Ready when data >= 120")
print("=" * 65)

conn.close()
