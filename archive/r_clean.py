import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT pair, pnl FROM trades WHERE pnl IS NOT NULL AND pnl != 0 AND pair IN ('EURUSD','GBPUSD') ORDER BY id")
trades = c.fetchall()

pnls = [t[1] for t in trades]
wins = [p for p in pnls if p > 0]
losses = [p for p in pnls if p < 0]

if not losses:
    print("No losses to normalize")
    conn.close()
    exit()

avg_loss = sum(abs(p) for p in losses) / len(losses)
r_values = [p / avg_loss for p in pnls]
avg_win_r = sum(wins) / len(wins) / avg_loss if wins else 0
expectancy = sum(r_values) / len(r_values)
wr = len(wins) / len(pnls) * 100

print("=" * 50)
print("  R-MULTIPLE ANALYSIS - Clean Experiment")
print("=" * 50)
print(f"  Trades: {len(r_values)}")
print(f"  Win Rate: {wr:.1f}% ({len(wins)}W / {len(losses)}L)")
print(f"  Avg Win R:   +{avg_win_r:.2f}R")
print(f"  Avg Loss R:  -1.00R (normalized)")
print(f"  R:R Ratio:   {avg_win_r:.2f}:1")
print(f"  Expectancy:  {expectancy:+.2f}R/trade")

print(f"\n  R Distribution (per trade):")
for lo, hi in [(-2,-1), (-1,0), (0,1), (1,2), (2,3), (3,6)]:
    count = len([r for r in r_values if lo <= r < hi])
    bar = "#" * count
    label = f"  {lo:+d}R to {hi:+d}R"
    print(f"{label:15s}: {count:2d} {bar}")

print(f"\n  Top 5 Wins (R multiples):")
sorted_wins = sorted([p/avg_loss for p in wins], reverse=True)
for r in sorted_wins[:5]:
    print(f"    +{r:.1f}R")

print(f"\n  Worst 5 Losses (R multiples):")
sorted_losses = sorted([p/avg_loss for p in losses])
for r in sorted_losses[:5]:
    print(f"    {r:.1f}R")

print("=" * 50)
conn.close()
