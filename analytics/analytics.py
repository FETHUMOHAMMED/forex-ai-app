"""
Trade Attribution Analytics
Reads from trades.db and prints performance by:
- Pair
- Regime
- Session (Asian / London / NY / Overlap)
- Confidence bucket

Also identifies top 3 and bottom 3 pairs by profit factor.
"""

import os
import sqlite3
from datetime import datetime
from collections import defaultdict

DB_PATH = "trades.db"

def get_session(timestamp :str):
    """Map entry_time (ISO string) to a session name."""
    try:
        dt = datetime.fromisoformat(timestamp)
        hour = dt.hour
        if 0 <= hour < 7:
            return "Asian"
        elif 7 <= hour < 13:
            return "London"
        elif 13 <= hour < 16:
            return "Overlap"
        else:
            return "NY"
    except:
        return "Unknown"

def get_confidence_bucket(conf):
    """Put confidence into a labelled bucket."""
    if conf is None:
        return "Unknown"
    if conf < 0.55:
        return "0.50–0.55"
    elif conf < 0.60:
        return "0.55–0.60"
    elif conf < 0.65:
        return "0.60–0.65"
    elif conf < 0.70:
        return "0.65–0.70"
    else:
        return "0.70+"

def compute_metrics(pnls):
    """Return (trades, wins, win_rate, total_pnl, profit_factor, expectancy)."""
    trades = len(pnls)
    if trades == 0:
        return (0, 0, 0.0, 0.0, 0.0, 0.0)
    wins = sum(1 for p in pnls if p > 0)
    win_rate = wins / trades * 100
    total_pnl = sum(pnls)
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss == 0:
        profit_factor = float('inf') if gross_profit > 0 else 0.0
    else:
        profit_factor = gross_profit / gross_loss
    expectancy = total_pnl / trades
    return (trades, wins, win_rate, total_pnl, profit_factor, expectancy)

def group_stats(groups, label_name):
    """Pretty‑print statistics for a grouping."""
    print(f"\n{'='*60}")
    print(f"📈 Performance by {label_name}")
    print(f"{'='*60}")
    print(f"{'Name':<20} {'Trades':>7} {'WR':>7} {'Net P&L':>10} {'PF':>8} {'Expectancy':>10}")
    print("-" * 62)
    for name, pnls in sorted(groups.items(), key=lambda x: sum(x[1]), reverse=True):
        t, w, wr, total, pf, exp = compute_metrics(pnls)
        pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
        print(f"{name:<20} {t:>7} {wr:>6.1f}% {total:>10.2f} {pf_str:>8} {exp:>10.2f}")

def main():
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'trades.db'))
    cursor = conn.cursor()

    # Fetch closed trades
    cursor.execute("""
        SELECT pair, signal, timestamp, exit_time, pnl, regime, confidence
        FROM trades
        WHERE exit_time IS NOT NULL AND pnl IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("⚠️ No closed trades found in the database.")
        return

    # Prepare grouping containers
    by_pair = defaultdict(list)
    by_regime = defaultdict(list)
    by_session = defaultdict(list)
    by_confidence = defaultdict(list)

    for pair, signal, timestamp_val, exit_time, pnl, regime, confidence in rows:
        by_pair[pair].append(pnl)
        by_regime[regime or "Unknown"].append(pnl)
        session = get_session(timestamp_val)
        by_session[session].append(pnl)
        bucket = get_confidence_bucket(confidence)
        by_confidence[bucket].append(pnl)

    # Print all sections
    group_stats(by_pair, "Pair")
    group_stats(by_regime, "Regime")
    group_stats(by_session, "Session")
    group_stats(by_confidence, "Confidence Bucket")

    # Top 3 & Bottom 3 pairs by profit factor
    pair_metrics = []
    for pair, pnls in by_pair.items():
        t, w, wr, total, pf, exp = compute_metrics(pnls)
        if pf != float('inf'):
            pair_metrics.append((pair, pf, total, t))
        else:
            pair_metrics.append((pair, 99.0, total, t))   # cap at 99 for sorting
    pair_metrics.sort(key=lambda x: x[1], reverse=True)

    print(f"\n{'='*60}")
    print("🏆 Top 3 Pairs by Profit Factor")
    for i, (pair, pf, total, t) in enumerate(pair_metrics[:3]):
        print(f"  {i+1}. {pair} – PF={pf:.2f}, Net=${total:.2f}, Trades={t}")

    print(f"\n🔻 Bottom 3 Pairs by Profit Factor")
    for i, (pair, pf, total, t) in enumerate(pair_metrics[-3:]):
        print(f"  {len(pair_metrics)-2+i}. {pair} – PF={pf:.2f}, Net=${total:.2f}, Trades={t}")

    # Save to file
    import sys
    orig_stdout = sys.stdout
    with open("analytics_report.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        # Re-run printing (simple approach)
        group_stats(by_pair, "Pair")
        group_stats(by_regime, "Regime")
        group_stats(by_session, "Session")
        group_stats(by_confidence, "Confidence Bucket")
        f.write("\n✅ Report saved\n")
    sys.stdout = orig_stdout
    print("\n📁 Report saved to analytics_report.txt")

if __name__ == "__main__":
    main()