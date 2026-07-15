import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 55)
print("  RULE IMPACT ANALYZER")
print("=" * 55)

c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
total = c.fetchone()[0]
c.execute("SELECT SUM(pnl) FROM trades WHERE pnl IS NOT NULL")
net_pnl = c.fetchone()[0] or 0

print(f"\n  Total trades: {total}, Net PnL: ${net_pnl:+.2f}")

# RULE 1: Low institutional score (<55 or NULL)
c.execute("""SELECT COUNT(*), ROUND(SUM(pnl),2), ROUND(AVG(pnl),2)
             FROM trades WHERE pnl IS NOT NULL 
             AND (institutional_score IS NULL OR institutional_score < 55)""")
cnt, saved, avg = c.fetchone()
print(f"\n  RULE 1 (Inst score <55):")
print(f"    Would reject: {cnt} trades")
print(f"    PnL avoided: ${saved:+.2f}")
print(f"    Avg PnL: ${avg}")

# RULE 2: Counter-trend
c.execute("""SELECT COUNT(*), ROUND(SUM(pnl),2), ROUND(AVG(pnl),2)
             FROM trades WHERE pnl IS NOT NULL 
             AND signal='BUY' AND (institutional_bias='BEARISH' OR regime='BEARISH')""")
cnt2, saved2, avg2 = c.fetchone()
c.execute("""SELECT COUNT(*), ROUND(SUM(pnl),2), ROUND(AVG(pnl),2)
             FROM trades WHERE pnl IS NOT NULL 
             AND signal='SELL' AND (institutional_bias='BULLISH' OR regime='BULLISH')""")
cnt3, saved3, avg3 = c.fetchone()
total_ct = (cnt2 or 0) + (cnt3 or 0)
total_saved = (saved2 or 0) + (saved3 or 0)
print(f"\n  RULE 2 (Counter-trend):")
print(f"    Would reject: {total_ct} trades")
print(f"    PnL avoided: ${total_saved:+.2f}")

# RULE 3: No liquidity event
c.execute("""SELECT COUNT(*), ROUND(SUM(pnl),2), ROUND(AVG(pnl),2)
             FROM trades WHERE pnl IS NOT NULL 
             AND (liquidity_state IS NULL OR liquidity_state LIKE '%NO%EVENT%' OR liquidity_state='BALANCED_VOLUME')""")
cnt4, saved4, avg4 = c.fetchone()
print(f"\n  RULE 3 (No liquidity event):")
print(f"    Would reject: {cnt4} trades")
print(f"    PnL avoided: ${saved4:+.2f}")
print(f"    Avg PnL: ${avg4}")

# RULE 4: NEUTRAL dealer pressure
c.execute("""SELECT COUNT(*), ROUND(SUM(pnl),2), ROUND(AVG(pnl),2)
             FROM trades WHERE pnl IS NOT NULL 
             AND (dealer_pressure IS NULL OR dealer_pressure='NEUTRAL')""")
cnt5, saved5, avg5 = c.fetchone()
print(f"\n  RULE 4 (NEUTRAL dealer):")
print(f"    Would reject: {cnt5} trades")
print(f"    PnL avoided: ${saved5:+.2f}")
print(f"    Avg PnL: ${avg5}")

# RULE 5: Low confidence (<0.53)
c.execute("""SELECT COUNT(*), ROUND(SUM(pnl),2), ROUND(AVG(pnl),2)
             FROM trades WHERE pnl IS NOT NULL 
             AND confidence < 0.53""")
cnt6, saved6, avg6 = c.fetchone()
print(f"\n  RULE 5 (Confidence <0.53):")
print(f"    Would reject: {cnt6} trades")
print(f"    PnL avoided: ${saved6:+.2f}")
print(f"    Avg PnL: ${avg6}")

# SUMMARY
print("\n" + "=" * 55)
print("  RULE IMPACT SUMMARY")
print("=" * 55)
rules = [
    ("Inst score <55", cnt or 0, saved or 0),
    ("Counter-trend", total_ct, total_saved),
    ("No liquidity", cnt4 or 0, saved4 or 0),
    ("NEUTRAL dealer", cnt5 or 0, saved5 or 0),
    ("Confidence <0.53", cnt6 or 0, saved6 or 0),
]
rules.sort(key=lambda x: x[2])

print(f"  {'Rule':<20s} {'Trades':>7s} {'PnL Saved':>10s}")
print(f"  {'-'*20} {'-'*7} {'-'*10}")
for name, cnt, saved in rules:
    print(f"  {name:<20s} {cnt:>7d} ${saved:>+9.2f}")

# If all rules were active
total_saved_all = sum(r[2] for r in rules)
remaining = total - max(r[1] for r in rules)  # Rough estimate
print(f"\n  If ALL rules active since start:")
print(f"    PnL saved: ${total_saved_all:+.2f}")
print(f"    Net would be: ${(net_pnl or 0) - total_saved_all:+.2f}")

print("=" * 55)
conn.close()
