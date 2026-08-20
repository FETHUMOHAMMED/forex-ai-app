import sqlite3
from datetime import datetime

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT pair, pnl, timestamp FROM trades WHERE pnl IS NOT NULL AND pnl != 0 AND pair IN ('EURUSD','GBPUSD') ORDER BY timestamp")
trades = c.fetchall()

pnls = [t[1] for t in trades]
losses = [p for p in pnls if p < 0]
avg_loss = sum(abs(p) for p in losses) / len(losses) if losses else 1

# Session buckets (UTC)
buckets = {
    "London Open (08-10)": (8, 10),
    "London Mid (10-13)": (10, 13),
    "London/NY Overlap (13-16)": (13, 16),
    "NY Continuation (16-19)": (16, 19),
    "Asian/Late (19-08)": (19, 8),  # overnight wrap
}

session_data = {name: [] for name in buckets}

for t in trades:
    pair, pnl, ts = t
    try:
        hour = datetime.fromisoformat(ts).hour
    except:
        continue
    r = pnl / avg_loss
    for name, (start, end) in buckets.items():
        if start < end:
            if start <= hour < end:
                session_data[name].append(r)
                break
        else:  # overnight wrap
            if hour >= start or hour < end:
                session_data[name].append(r)
                break

print("=" * 55)
print("  EXPECTANCY BY SESSION - Clean Experiment")
print("=" * 55)
print(f"  {'Session':<25s} {'Trades':>6s} {'Win%':>6s} {'Expect':>8s} {'Distribution'}")
print(f"  {'-'*25} {'-'*6} {'-'*6} {'-'*8} {'-'*17}")

for name in buckets:
    r_vals = session_data[name]
    if not r_vals:
        continue
    wins = [r for r in r_vals if r > 0]
    wr = len(wins)/len(r_vals)*100
    expect = sum(r_vals)/len(r_vals)
    best = max(r_vals)
    worst = min(r_vals)
    
    # Visual distribution
    pos_bars = int(max(0, expect) * 5)
    neg_bars = int(abs(min(0, expect)) * 5)
    bar = ("#" * pos_bars) if expect > 0 else ("-" * neg_bars)
    
    star = " *** BEST ***" if expect > 0.3 else ""
    print(f"  {name:<25s} {len(r_vals):>6d} {wr:>5.0f}% {expect:>+7.2f}R   W:{best:+.1f}R L:{worst:+.1f}R{star}")

print(f"\n  Total clean trades: {len(trades)}")
print(f"  Overall expectancy: {sum(pnls)/len(pnls)/avg_loss:+.2f}R")
print("=" * 55)
conn.close()
