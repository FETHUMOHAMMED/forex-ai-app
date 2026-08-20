import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 60)
print("  ABLATION STUDY - Which filters add value?")
print("=" * 60)

# Use shadow trades (1644 trades) for statistical power
c.execute("SELECT COUNT(*) FROM shadow_trades WHERE decision='SIMULATED' AND simulated_result!='PENDING'")
total = c.fetchone()[0]
print(f"\n  Dataset: {total} shadow trades")

# Strategy A: ML AND ICT (current)
c.execute("""SELECT COUNT(*), 
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1),
             ROUND(SUM(simulated_pnl),2)
             FROM shadow_trades WHERE decision='SIMULATED' AND simulated_result!='PENDING'
             AND confidence IS NOT NULL""")
t, wr, pnl = c.fetchone()
print(f"\n  Strategy A (ML + ICT, current): {t} trades, {wr}% WR, PnL ${pnl}")

# Strategy B: Institutional >= 60 + ICT (no ML)
c.execute("""SELECT COUNT(*), 
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1),
             ROUND(SUM(simulated_pnl),2)
             FROM shadow_trades WHERE decision='SIMULATED' AND simulated_result!='PENDING'
             AND institutional_score >= 60""")
t2, wr2, pnl2 = c.fetchone()
print(f"\n  Strategy B (Inst>=60 + ICT, no ML): {t2} trades, {wr2}% WR, PnL ${pnl2}")

# Strategy C: Institutional >= 60 + Confidence >= 0.53
c.execute("""SELECT COUNT(*), 
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1),
             ROUND(SUM(simulated_pnl),2)
             FROM shadow_trades WHERE decision='SIMULATED' AND simulated_result!='PENDING'
             AND institutional_score >= 60 AND confidence >= 0.53""")
t3, wr3, pnl3 = c.fetchone()
print(f"\n  Strategy C (Inst>=60 + Conf>=0.53): {t3} trades, {wr3}% WR, PnL ${pnl3}")

# Strategy D: Institutional >= 60 only (no ML, no ICT)
c.execute("""SELECT COUNT(*), 
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1),
             ROUND(SUM(simulated_pnl),2)
             FROM shadow_trades WHERE decision='SIMULATED' AND simulated_result!='PENDING'
             AND institutional_score >= 60""")
t4, wr4, pnl4 = c.fetchone()
print(f"\n  Strategy D (Inst>=60 only): {t4} trades, {wr4}% WR, PnL ${pnl4}")

# Distribution of institutional scores
print(f"\n  Institutional Score Distribution:")
c.execute("""SELECT CASE 
             WHEN institutional_score >= 80 THEN '80-100'
             WHEN institutional_score >= 60 THEN '60-79'
             WHEN institutional_score >= 40 THEN '40-59'
             WHEN institutional_score > 0 THEN '1-39'
             ELSE '0/UNKNOWN'
             END as bucket,
             COUNT(*),
             ROUND(AVG(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END)*100,1)
             FROM shadow_trades WHERE decision='SIMULATED'
             GROUP BY bucket ORDER BY bucket DESC""")
for r in c.fetchall():
    print(f"    {r[0]:12s}: {r[1]:4d} trades, {r[2]}% WR")

print("\n" + "=" * 60)
conn.close()
