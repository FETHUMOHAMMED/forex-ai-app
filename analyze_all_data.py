import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print('=' * 65)
print('  COMPLETE DATA ANALYSIS — 120+ DATA POINTS')
print('=' * 65)

# Total counts
c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
real = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM shadow_trades")
shadow = c.fetchone()[0]
total = real + shadow
print('\n1. DATA VOLUME')
print('   Real trades: ' + str(real))
print('   Shadow trades: ' + str(shadow))
print('   COMBINED: ' + str(total) + (' >= 120 TARGET REACHED' if total >= 120 else ' (need ' + str(120-total) + ' more)'))

# Regime analysis
print('\n2. REGIME PERFORMANCE')
c.execute("""SELECT regime, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END),
             ROUND(AVG(confidence), 3)
             FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL
             GROUP BY regime ORDER BY COUNT(*) DESC""")
for row in c.fetchall():
    wr = row[2]/row[1]*100 if row[1] > 0 else 0
    bar = '#' * int(wr/5)
    print('   ' + str(row[0]) + ': ' + str(row[1]) + ' trades, ' + str(round(wr)) + '% WR ' + bar)
    print('     Avg confidence: ' + str(row[3]))

# Pair ranking
print('\n3. PAIR RANKING')
c.execute("""SELECT pair, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END),
             ROUND(AVG(confidence), 3), ROUND(AVG(opportunity_score), 1)
             FROM shadow_trades WHERE decision='SIMULATED'
             GROUP BY pair ORDER BY COUNT(*) DESC""")
print('   Pair        Trades   WR      AvgConf  AvgScore  Recommendation')
print('   ' + '-' * 62)
for row in c.fetchall():
    wr = row[2]/row[1]*100 if row[1] > 0 else 0
    rec = 'KEEP' if wr >= 40 else 'WATCH' if wr >= 30 else 'DROP'
    print('   ' + str(row[0]).ljust(12) + str(row[1]).ljust(9) + str(round(wr)).ljust(7) + str(row[3]).ljust(9) + str(row[4]).ljust(10) + rec)

# Regime x Pair (best combos)
print('\n4. BEST REGIME x PAIR COMBINATIONS (min 5 trades)')
c.execute("""SELECT regime, pair, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)
             FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL
             GROUP BY regime, pair HAVING COUNT(*) >= 5
             ORDER BY COUNT(*) DESC""")
for row in c.fetchall():
    wr = row[3]/row[2]*100 if row[2] > 0 else 0
    star = ' *HIGH WIN*' if wr >= 60 else ''
    print('   ' + str(row[0]).ljust(15) + str(row[1]).ljust(10) + str(row[2]) + ' trades, ' + str(round(wr)) + '% WR' + star)

# Confidence calibration
print('\n5. CONFIDENCE vs WIN RATE')
brackets = [(0.50, 0.53), (0.53, 0.56), (0.56, 0.60), (0.60, 0.70)]
for lo, hi in brackets:
    c.execute("""SELECT COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)
                 FROM shadow_trades WHERE decision='SIMULATED'
                 AND confidence >= ? AND confidence < ?""", (lo, hi))
    row = c.fetchone()
    if row[0] > 0:
        wr = row[1]/row[0]*100
        print('   Conf ' + str(lo) + '-' + str(hi) + ': ' + str(row[0]) + ' trades, ' + str(round(wr)) + '% WR')

# Grade calibration
print('\n6. GRADE vs WIN RATE')
c.execute("""SELECT grade, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)
             FROM shadow_trades WHERE decision='SIMULATED' AND grade IS NOT NULL
             GROUP BY grade ORDER BY grade""")
for row in c.fetchall():
    wr = row[2]/row[1]*100 if row[1] > 0 else 0
    print('   Grade ' + str(row[0]) + ': ' + str(row[1]) + ' trades, ' + str(round(wr)) + '% WR')

# Key recommendations
print('\n7. RECOMMENDATIONS FOR VOLUME 9')
print('   Based on ' + str(total) + ' data points:')
print()

# Best regime
c.execute("""SELECT regime, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)
             FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL
             GROUP BY regime ORDER BY COUNT(*) DESC LIMIT 1""")
best_regime = c.fetchone()
if best_regime:
    wr = best_regime[2]/best_regime[1]*100
    print('   1. Best regime: ' + str(best_regime[0]) + ' (' + str(round(wr)) + '% WR, ' + str(best_regime[1]) + ' trades)')
    print('      -> Volume 9: Increase confidence in ' + str(best_regime[0]) + ' regime')

# Worst regime
c.execute("""SELECT regime, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)
             FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL
             GROUP BY regime ORDER BY COUNT(*) DESC""")
regimes = c.fetchall()
worst = min(regimes, key=lambda r: r[2]/r[1]*100 if r[1] > 0 else 100)
if worst:
    wr = worst[2]/worst[1]*100 if worst[1] > 0 else 0
    print('   2. Worst regime: ' + str(worst[0]) + ' (' + str(round(wr)) + '% WR)')
    print('      -> Volume 9: Reduce/block trades in ' + str(worst[0]) + ' regime')

# Best pair
c.execute("""SELECT pair, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)
             FROM shadow_trades WHERE decision='SIMULATED'
             GROUP BY pair HAVING COUNT(*) >= 5 ORDER BY COUNT(*) DESC""")
pairs = c.fetchall()
if pairs:
    # Sort by WR
    sorted_pairs = sorted(pairs, key=lambda r: r[2]/r[1]*100 if r[1] > 0 else 0, reverse=True)
    best_pair = sorted_pairs[0]
    wr = best_pair[2]/best_pair[1]*100 if best_pair[1] > 0 else 0
    print('   3. Best pair: ' + str(best_pair[0]) + ' (' + str(round(wr)) + '% WR)')
    
    # Drop candidates
    drop_candidates = [p for p in sorted_pairs if (p[2]/p[1]*100 if p[1] > 0 else 0) < 35]
    if drop_candidates:
        drops = ', '.join([p[0] + ' (' + str(round(p[2]/p[1]*100)) + '%)' for p in drop_candidates])
        print('   4. Drop candidates: ' + drops)

# Session
print('\n   5. Session filter: London + Asian only (NY/Overlap blocked)')
print('      -> Volume 9: Enforce session-based confidence adjustment')

print('\n' + '=' * 65)
print('  ANALYSIS COMPLETE — READY FOR VOLUME 9 WHEN 120+ REACHED')
print('=' * 65)

conn.close()
