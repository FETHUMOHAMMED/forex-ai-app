import sqlite3
from datetime import datetime

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT pair, pnl, timestamp FROM trades WHERE pnl IS NOT NULL AND pnl != 0 AND pair IN ('EURUSD','GBPUSD') ORDER BY timestamp")
trades = c.fetchall()

# Calculate avg loss for R normalization
pnls = [t[1] for t in trades]
losses = [p for p in pnls if p < 0]
avg_loss = sum(abs(p) for p in losses) / len(losses) if losses else 1

# Group by hour
hours = {}
for t in trades:
    pair, pnl, ts = t
    try:
        dt = datetime.fromisoformat(ts)
        hour = dt.hour
    except:
        continue
    if hour not in hours:
        hours[hour] = []
    hours[hour].append(pnl / avg_loss)

print("=" * 55)
print("  EXPECTANCY BY HOUR (UTC) - Clean Experiment")
print("=" * 55)
print(f"  {'Hour':<8s} {'Trades':>6s} {'Win%':>6s} {'Expect':>8s} {'Best':>7s} {'Worst':>7s}")
print(f"  {'-'*8} {'-'*6} {'-'*6} {'-'*8} {'-'*7} {'-'*7}")

for hour in sorted(hours.keys()):
    r_vals = hours[hour]
    wins = [r for r in r_vals if r > 0]
    wr = len(wins)/len(r_vals)*100
    expect = sum(r_vals)/len(r_vals)
    best = max(r_vals)
    worst = min(r_vals)
    bar = "#" * int(abs(expect)*5) if expect > 0 else "-" * int(abs(expect)*5)
    print(f"  {hour:02d}:00   {len(r_vals):>6d} {wr:>5.0f}% {expect:>+7.2f}R {best:>+6.1f}R {worst:>+6.1f}R  {bar}")

print("=" * 55)
conn.close()
