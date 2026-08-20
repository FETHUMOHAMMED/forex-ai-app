import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 50)
print("  R-ANALYSIS BY PAIR - Clean Experiment")
print("=" * 50)

for pair in ['EURUSD', 'GBPUSD']:
    c.execute("SELECT pnl FROM trades WHERE pnl IS NOT NULL AND pnl != 0 AND pair = ? ORDER BY id", (pair,))
    trades = c.fetchall()
    pnls = [t[0] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    
    if not losses:
        print(f"\n  {pair}: No losses to normalize")
        continue
    
    avg_loss = sum(abs(p) for p in losses) / len(losses)
    r_values = [p / avg_loss for p in pnls]
    avg_win_r = sum(wins) / len(wins) / avg_loss if wins else 0
    expectancy = sum(r_values) / len(r_values)
    wr = len(wins) / len(pnls) * 100
    
    print(f"\n  {pair} ({len(pnls)} trades):")
    print(f"    Win Rate:     {wr:.1f}% ({len(wins)}W / {len(losses)}L)")
    print(f"    Avg Win R:    +{avg_win_r:.2f}R")
    print(f"    Avg Loss R:   -1.00R")
    print(f"    R:R Ratio:    {avg_win_r:.2f}:1")
    print(f"    Expectancy:   {expectancy:+.2f}R/trade")
    print(f"    Best Win:     +{max(r_values):.1f}R")
    print(f"    Worst Loss:   {min(r_values):.1f}R")

# Losses beyond 1R investigation
print(f"\n  --- LOSSES BEYOND -1R ---")
c.execute("SELECT pair, pnl, entry, stop_loss, exit_price FROM trades WHERE pnl IS NOT NULL AND pnl < 0 AND pair IN ('EURUSD','GBPUSD') ORDER BY id")
all_losses = c.fetchall()
avg_l = sum(abs(t[1]) for t in all_losses) / len(all_losses) if all_losses else 1
big_losses = [t for t in all_losses if abs(t[1])/avg_l > 1.2]
print(f"  Trades exceeding 1.2R: {len(big_losses)}/{len(all_losses)}")
for t in big_losses:
    r = abs(t[1]) / avg_l
    print(f"  {t[0]}: -${abs(t[1]):.0f} ({-r:.1f}R) entry={t[2]} sl={t[3]} exit={t[4]}")

print("=" * 50)
conn.close()
