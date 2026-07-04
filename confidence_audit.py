"""
Confidence Calibration Audit
Reads closed trades from trades.db and prints performance by confidence bucket.
"""

import sqlite3
from collections import defaultdict

DB_PATH = "trades.db"

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
    elif conf < 0.75:
        return "0.70–0.75"
    else:
        return "0.75+"

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

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch closed trades that have a confidence value
    cursor.execute("""
        SELECT confidence, pnl
        FROM trades
        WHERE exit_time IS NOT NULL AND pnl IS NOT NULL AND confidence IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("⚠️ No closed trades with confidence data found. Wait for more trades to close.")
        return

    by_bucket = defaultdict(list)
    for confidence, pnl in rows:
        bucket = get_confidence_bucket(confidence)
        by_bucket[bucket].append(pnl)

    # Print report
    print(f"\n{'='*70}")
    print("📊 CONFIDENCE CALIBRATION AUDIT")
    print(f"{'='*70}")
    print(f"{'Confidence Bucket':<20} {'Trades':>7} {'WR':>7} {'Net P&L':>10} {'PF':>8} {'Expectancy':>10}")
    print("-" * 62)

    for bucket in ["0.50–0.55", "0.55–0.60", "0.60–0.65", "0.65–0.70", "0.70–0.75", "0.75+"]:
        pnls = by_bucket.get(bucket, [])
        if not pnls:
            continue
        t, w, wr, total, pf, exp = compute_metrics(pnls)
        pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
        print(f"{bucket:<20} {t:>7} {wr:>6.1f}% {total:>10.2f} {pf_str:>8} {exp:>10.2f}")

    # Recommendation
    print(f"\n{'='*70}")
    print("🔧 RECOMMENDATION")
    print(f"{'='*70}")
    found_threshold = None
    for bucket in ["0.50–0.55", "0.55–0.60", "0.60–0.65", "0.65–0.70", "0.70–0.75", "0.75+"]:
        pnls = by_bucket.get(bucket, [])
        if len(pnls) >= 3:
            _, _, _, total, pf, _ = compute_metrics(pnls)
            if total > 0 and pf >= 1.0:
                if found_threshold is None:
                    found_threshold = bucket.split("–")[0]
                    break

    if found_threshold:
        print(f"✅ Trades become profitable at confidence >= {found_threshold}")
        print(f"   Suggested min_confidence = {found_threshold}")
    else:
        print("⚠️ Not enough data to determine optimal threshold. Re-run after more trades close.")

if __name__ == "__main__":
    main()