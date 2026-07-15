import sqlite3
from itertools import combinations
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT id, pair, signal, pnl, confidence, institutional_score, dealer_pressure, liquidity_state, institutional_bias FROM trades WHERE pnl IS NOT NULL AND pnl != 0")
trades = c.fetchall()
total_trades = len(trades)

rules = {
    "Inst<55": lambda t: (t[5] or 0) < 55,
    "Dealer=NEUT": lambda t: (t[6] or 'NEUTRAL') == 'NEUTRAL',
    "Conf<0.53": lambda t: (t[4] or 0) < 0.53,
    "NoLiq": lambda t: ('NO_EVENT' in str(t[7] or '') or 'BALANCED' in str(t[7] or '')),
}

print("=" * 65)
print("  PARETO FRONTIER - Best Rule Combinations")
print("=" * 65)
print(f"  Total trades analyzed: {total_trades}")
print(f"  {'Combo':<30s} {'Kept':>5s} {'WR':>6s} {'PF':>6s} {'Expect':>7s} {'NetPnL':>8s}")
print(f"  {'-'*30} {'-'*5} {'-'*6} {'-'*6} {'-'*7} {'-'*8}")

results = []

# No rules
kept_all = trades
w_all = sum(1 for t in kept_all if t[3] > 0)
l_all = sum(1 for t in kept_all if t[3] < 0)
gross = sum(t[3] for t in kept_all if t[3] > 0)
loss = abs(sum(t[3] for t in kept_all if t[3] < 0))
wr = w_all/len(kept_all)*100 if kept_all else 0
pf = gross/loss if loss > 0 else 999
expect = sum(t[3] for t in kept_all)/len(kept_all) if kept_all else 0
results.append(("No rules", len(kept_all), wr, pf, expect, sum(t[3] for t in kept_all)))

# Test all combinations of rules
best_combos = []
for r in range(1, len(rules)+1):
    for combo in combinations(rules.keys(), r):
        rule_fns = [rules[name] for name in combo]
        kept = [t for t in trades if not any(fn(t) for fn in rule_fns)]
        
        if len(kept) < 10:  # Minimum 10 trades for validity
            continue
            
        w = sum(1 for t in kept if t[3] > 0)
        l = sum(1 for t in kept if t[3] < 0)
        gross = sum(t[3] for t in kept if t[3] > 0)
        loss_val = abs(sum(t[3] for t in kept if t[3] < 0))
        wr = w/len(kept)*100
        pf = gross/loss_val if loss_val > 0 else 999
        expect = sum(t[3] for t in kept)/len(kept)
        net = sum(t[3] for t in kept)
        
        combo_name = "+".join(combo)
        best_combos.append((combo_name, len(kept), wr, pf, expect, net))

# Sort by expectancy (best first)
best_combos.sort(key=lambda x: x[4], reverse=True)

for combo_name, kept_n, wr, pf, expect, net in best_combos[:15]:
    print(f"  {combo_name:<30s} {kept_n:>5d} {wr:>5.0f}% {pf:>5.2f} ${expect:>+6.2f} ${net:>+7.2f}")

# No rules baseline
print(f"\n  BASELINE (no rules):")
print(f"  {total_trades} trades, {w_all/len(kept_all)*100:.0f}% WR, PF={pf:.2f}, Expect=${sum(t[3] for t in kept_all)/len(kept_all):+.2f}")

# Best recommendation
if best_combos:
    best = best_combos[0]
    print(f"\n  RECOMMENDED: {best[0]}")
    print(f"  Keeps {best[1]}/{total_trades} trades ({best[1]/total_trades*100:.0f}%)")
    print(f"  WR: {best[2]:.0f}% | PF: {best[3]:.2f} | Expect: ${best[4]:+.2f}/trade")

print("=" * 65)
conn.close()
