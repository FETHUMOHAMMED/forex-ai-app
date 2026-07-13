import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 60)
print("  DATA QUALITY REPORT - 1087 Data Points")
print("=" * 60)

# 1. TOTAL
c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
real = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM shadow_trades")
shadow = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM research_decisions")
research = c.fetchone()[0]
total = real + shadow + research
print(f"\n1. TOTAL: {total} ({real} real + {shadow} shadow + {research} research)")

# 2. PAIR DISTRIBUTION
print("\n2. PAIR DISTRIBUTION")
print("   Real trades:")
c.execute("SELECT pair, COUNT(*) FROM trades WHERE pnl IS NOT NULL GROUP BY pair ORDER BY COUNT(*) DESC")
for row in c.fetchall():
    print(f"     {row[0]:10s}: {row[1]:3d}")

print("   Research decisions:")
c.execute("SELECT pair, COUNT(*) FROM research_decisions GROUP BY pair ORDER BY COUNT(*) DESC")
for row in c.fetchall():
    print(f"     {row[0]:10s}: {row[1]:3d}")

# 3. REGIME DISTRIBUTION
print("\n3. REGIME DISTRIBUTION (shadow trades)")
c.execute("SELECT regime, COUNT(*), ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 100 ELSE 0 END),1) FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL GROUP BY regime ORDER BY COUNT(*) DESC")
for row in c.fetchall():
    print(f"   {row[0]:15s}: {row[1]:3d} trades, {row[2]}% WR")

# 4. GRADE DISTRIBUTION
print("\n4. GRADE DISTRIBUTION (research)")
c.execute("SELECT grade, COUNT(*) FROM research_decisions GROUP BY grade ORDER BY grade")
for row in c.fetchall():
    print(f"   Grade {row[0]}: {row[1]:3d}")

# 5. DECISION DISTRIBUTION
print("\n5. DECISION DISTRIBUTION (research)")
c.execute("SELECT decision, COUNT(*) FROM research_decisions GROUP BY decision")
for row in c.fetchall():
    print(f"   {row[0]:15s}: {row[1]:3d}")

# 6. REGIME BY PAIR (shadow)
print("\n6. BEST REGIME x PAIR (shadow, min 10 trades)")
c.execute("""SELECT pair, regime, COUNT(*), ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 100 ELSE 0 END),1)
             FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL
             GROUP BY pair, regime HAVING COUNT(*) >= 10 ORDER BY AVG(CASE WHEN simulated_result='WIN' THEN 100 ELSE 0 END) DESC LIMIT 10""")
for row in c.fetchall():
    print(f"   {row[0]:8s} + {row[1]:12s}: {row[2]:3d} trades, {row[3]}% WR")

# 7. GAPS
print("\n7. DATA GAPS")
print("   Regimes with <20 samples:")
c.execute("""SELECT regime, COUNT(*) FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL GROUP BY regime HAVING COUNT(*) < 20""")
gaps = c.fetchall()
if gaps:
    for g in gaps:
        print(f"     {g[0]}: {g[1]} trades - NEED MORE")
else:
    print("     None! All regimes well-sampled.")

print("\n   Pairs with <30 real trades:")
c.execute("""SELECT pair, COUNT(*) FROM trades WHERE pnl IS NOT NULL GROUP BY pair HAVING COUNT(*) < 10""")
gaps = c.fetchall()
if gaps:
    for g in gaps:
        print(f"     {g[0]}: {g[1]} trades - NEED MORE")
else:
    print("     None!")

# 8. RECOMMENDATIONS
print("\n8. RECOMMENDATIONS FOR VOLUME 10")
print("   Based on 1087 data points:")
c.execute("""SELECT pair, COUNT(*), ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 100 ELSE 0 END),1)
             FROM shadow_trades WHERE decision='SIMULATED'
             GROUP BY pair HAVING COUNT(*) >= 20 ORDER BY AVG(CASE WHEN simulated_result='WIN' THEN 100 ELSE 0 END) DESC LIMIT 5""")
top_pairs = c.fetchall()
if top_pairs:
    print(f"   1. Focus live trading on: {', '.join([p[0] for p in top_pairs])}")

c.execute("""SELECT regime, COUNT(*), ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 100 ELSE 0 END),1)
             FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL
             GROUP BY regime HAVING COUNT(*) >= 20 ORDER BY AVG(CASE WHEN simulated_result='WIN' THEN 100 ELSE 0 END) ASC LIMIT 3""")
worst = c.fetchall()
if worst:
    print(f"   2. Avoid regimes: {', '.join([w[0] for w in worst])}")

print("   3. Collect 100+ real demo trades before Volume 10")
print("   4. Add outcome tracking to research decisions")

print("\n" + "=" * 60)

conn.close()
