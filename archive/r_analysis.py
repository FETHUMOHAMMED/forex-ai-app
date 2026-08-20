import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 55)
print("  R-MULTIPLE ANALYSIS - Clean Experiment")
print("=" * 55)

# EURUSD + GBPUSD trades with entry/sl data
c.execute("""SELECT pair, signal, pnl, entry, stop_loss, exit_price FROM trades 
             WHERE pnl IS NOT NULL AND pnl != 0 
             AND pair IN ('EURUSD','GBPUSD') 
             AND entry IS NOT NULL AND stop_loss IS NOT NULL AND exit_price IS NOT NULL
             ORDER BY id""")
trades = c.fetchall()

if not trades:
    print("  No trades with entry/SL data")
    conn.close()
    exit()

r_values = []
wins_r = []
losses_r = []

for t in trades:
    pair, signal, pnl, entry, sl, exit_p = t
    risk = abs(entry - sl)
    if risk > 0:
        r = pnl / risk
        r_values.append(r)
        if pnl > 0:
            wins_r.append(r)
        else:
            losses_r.append(r)

print(f"\n  Trades with R data: {len(r_values)}")
print(f"  Avg R per trade:   {sum(r_values)/len(r_values):+.2f}R")
print(f"  Median R:          {sorted(r_values)[len(r_values)//2]:+.2f}R")
print(f"  Max favorable R:   {max(r_values):+.2f}R")
print(f"  Max adverse R:     {min(r_values):+.2f}R")

if wins_r:
    print(f"\n  Winners ({len(wins_r)}):")
    print(f"    Avg win R:       {sum(wins_r)/len(wins_r):+.2f}R")
    print(f"    Best win R:      {max(wins_r):+.2f}R")
    print(f"    Worst win R:     {min(wins_r):+.2f}R")

if losses_r:
    print(f"\n  Losers ({len(losses_r)}):")
    print(f"    Avg loss R:      {sum(losses_r)/len(losses_r):+.2f}R")
    print(f"    Best loss R:     {max(losses_r):+.2f}R")
    print(f"    Worst loss R:    {min(losses_r):+.2f}R")

# R distribution
print(f"\n  R Distribution:")
bins = [(-3, -2), (-2, -1), (-1, 0), (0, 1), (1, 2), (2, 3), (3, 5)]
for lo, hi in bins:
    count = len([r for r in r_values if lo <= r < hi])
    bar = '#' * count
    print(f"  {lo:+.0f}R to {hi:+.0f}R: {count:2d} {bar}")

# Expectancy in R terms
avg_win_r = sum(wins_r)/len(wins_r) if wins_r else 0
avg_loss_r = sum(losses_r)/len(losses_r) if losses_r else 0
wr = len(wins_r)/len(r_values)*100 if r_values else 0
expectancy_r = (wr/100 * avg_win_r) - ((100-wr)/100 * abs(avg_loss_r))
print(f"\n  Expectancy:        {expectancy_r:+.2f}R/trade")
print(f"  Win Rate:          {wr:.1f}%")
print(f"  Reward:Risk Ratio: {abs(avg_win_r/avg_loss_r):.2f}" if avg_loss_r else "")

print("=" * 55)
conn.close()
