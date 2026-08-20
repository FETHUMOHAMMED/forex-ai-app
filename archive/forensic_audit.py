import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 65)
print("  FORENSIC AUDIT - Last 10 GBPUSD Trades")
print("=" * 65)

c.execute("""SELECT pair, signal, pnl, confidence, entry, exit_price, stop_loss,
             institutional_score, dealer_pressure, liquidity_state, regime, timestamp
             FROM trades WHERE pair='GBPUSD' AND pnl IS NOT NULL AND pnl != 0
             ORDER BY id DESC LIMIT 10""")

for i, r in enumerate(c.fetchall()):
    pair, sig, pnl, conf, entry, exit_p, sl, inst, dealer, liq, regime, ts = r
    print(f"\n--- Trade #{10-i} ---")
    print(f"  Time:     {ts[:19]}")
    print(f"  Signal:   {sig} | Conf: {conf} | Inst: {inst} | Regime: {regime}")
    print(f"  Dealer:   {dealer} | Liq: {liq}")
    print(f"  Entry:    {entry:.5f} | Exit: {exit_p:.5f} | SL: {sl:.5f}")
    print(f"  PnL:      ${pnl:+.2f}")
    
    # Analyze
    if conf and conf < 0.51:
        print(f"  WARNING:  Confidence {conf:.3f} barely above 0.50")
    if inst == 0 or inst is None:
        print(f"  WARNING:  Institutional score = 0 - filter not active")
    if dealer == 'NEUTRAL':
        print(f"  WARNING:  No dealer pressure signal")
    if liq and 'NO_EVENT' in str(liq):
        print(f"  WARNING:  No liquidity event detected")

# Summary
c.execute("""SELECT COUNT(*), SUM(pnl), AVG(pnl), 
             SUM(CASE WHEN institutional_score=0 OR institutional_score IS NULL THEN 1 ELSE 0 END),
             SUM(CASE WHEN dealer_pressure='NEUTRAL' THEN 1 ELSE 0 END)
             FROM trades WHERE pair='GBPUSD' AND pnl IS NOT NULL AND pnl != 0
             ORDER BY id DESC LIMIT 20""")
r = c.fetchone()
print(f"\n{'='*65}")
print(f"  LAST 20 GBPUSD SUMMARY:")
print(f"  Trades: {r[0]} | Total PnL: ${r[1]:+.2f} | Avg: ${r[2]:+.2f}")
print(f"  With Inst=0: {r[3]}/{r[0]}")
print(f"  With Dealer=NEUTRAL: {r[4]}/{r[0]}")
print("=" * 65)
conn.close()
