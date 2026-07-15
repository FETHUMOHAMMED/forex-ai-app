import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT id, pair, signal, pnl, confidence, institutional_score, dealer_pressure, liquidity_state, institutional_bias FROM trades WHERE pnl IS NOT NULL AND pnl != 0")
trades = c.fetchall()

print("=" * 60)
print("  RULE IMPACT V2 - Non-overlapping, with winners counted")
print("=" * 60)

rules = {
    "Inst <55": lambda t: (t[5] or 0) < 55,
    "NEUTRAL dealer": lambda t: (t[6] or 'NEUTRAL') == 'NEUTRAL',
    "Conf <0.53": lambda t: (t[4] or 0) < 0.53,
    "No liquidity": lambda t: ('NO_EVENT' in str(t[7] or '') or 'BALANCED' in str(t[7] or '')),
    "Counter-trend": lambda t: (t[1] == 'BUY' and 'BEARISH' in str(t[8] or '')) or (t[1] == 'SELL' and 'BULLISH' in str(t[8] or '')),
}

# Individual rule analysis
print("\n--- INDIVIDUAL RULES ---")
print(f"  {'Rule':<18s} {'Rej':>4s} {'WinRej':>6s} {'LossRej':>7s} {'NetEffect':>10s} {'Verdict':>8s}")
print(f"  {'-'*18} {'-'*4} {'-'*6} {'-'*7} {'-'*10} {'-'*8}")

for rule_name, rule_fn in rules.items():
    rejected = [t for t in trades if rule_fn(t)]
    wins_rejected = sum(1 for t in rejected if t[3] > 0)
    losses_rejected = sum(1 for t in rejected if t[3] < 0)
    pnl_wins = sum(t[3] for t in rejected if t[3] > 0)
    pnl_losses = sum(t[3] for t in rejected if t[3] < 0)
    net_effect = -(pnl_wins + pnl_losses)  # PnL avoided = negative of what happened
    verdict = "KEEP" if net_effect > 0 else "DROP"
    print(f"  {rule_name:<18s} {len(rejected):>4d} {wins_rejected:>6d} {losses_rejected:>7d} ${net_effect:>+9.2f} {verdict:>8s}")

# Combined: all rules active
print("\n--- ALL RULES COMBINED ---")
rejected_any = []
kept = []
for t in trades:
    if any(rule_fn(t) for rule_fn in rules.values()):
        rejected_any.append(t)
    else:
        kept.append(t)

wins_rej = sum(1 for t in rejected_any if t[3] > 0)
losses_rej = sum(1 for t in rejected_any if t[3] < 0)
pnl_rej_wins = sum(t[3] for t in rejected_any if t[3] > 0)
pnl_rej_losses = sum(t[3] for t in rejected_any if t[3] < 0)
net_saved = -(pnl_rej_wins + pnl_rej_losses)

print(f"  Total trades: {len(trades)}")
print(f"  Rejected: {len(rejected_any)} ({wins_rej} wins, {losses_rej} losses)")
print(f"  Kept: {len(kept)}")
print(f"  PnL of rejected: ${pnl_rej_wins+pnl_rej_losses:+.2f}")
print(f"  Net improvement: ${net_saved:+.2f}")

if kept:
    kept_wins = sum(1 for t in kept if t[3] > 0)
    kept_losses = sum(1 for t in kept if t[3] < 0)
    kept_gross = sum(t[3] for t in kept if t[3] > 0)
    kept_loss = abs(sum(t[3] for t in kept if t[3] < 0))
    kept_wr = kept_wins/len(kept)*100
    kept_pf = kept_gross/kept_loss if kept_loss > 0 else 999
    kept_expect = sum(t[3] for t in kept)/len(kept)
    
    print(f"\n  KEPT TRADES PERFORMANCE:")
    print(f"  Trades: {len(kept)}")
    print(f"  Win Rate: {kept_wr:.1f}%")
    print(f"  Profit Factor: {kept_pf:.2f}")
    print(f"  Expectancy: ${kept_expect:+.2f}/trade")
    print(f"  Total PnL: ${sum(t[3] for t in kept):+.2f}")

print("\n" + "=" * 60)
conn.close()
