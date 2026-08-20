# -*- coding: utf-8 -*-
"""Validation Mode - Honest assessment with statistical warnings"""
import sys
from pathlib import Path
sys.path.insert(0, '.')
from tools.common import get_db, check_mt5

def get_validation_status():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("""
        SELECT COUNT(*), SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),
               COALESCE(SUM(pnl), 0)
        FROM trades
        WHERE strategy_version = 'V3_REGIME' 
        AND account = 'Live_Micro'
        AND result IN ('WIN', 'LOSS', 'BREAKEVEN')
        AND mt5_position_id IS NOT NULL
        AND exit_time IS NOT NULL AND pnl IS NOT NULL
        AND entry != 1.15123
    """)
    
    row = c.fetchone()
    total, wins, pnl = row
    win_rate = (wins / total * 100) if total > 0 else 0
    
    c.execute("SELECT COUNT(*), COALESCE(SUM(pnl), 0) FROM trades WHERE strategy_version = 'PRE_V3'")
    pre_v3 = c.fetchone()
    
    c.execute("SELECT COUNT(*) FROM trades WHERE strategy_version = 'V3_REGIME' AND account != 'Live_Micro'")
    demo = c.fetchone()[0]
    
    mt5 = check_mt5()
    
    conn.close()
    
    return {
        "v3_closed": total, "v3_wins": wins, "v3_pnl": pnl, "v3_wr": win_rate,
        "pre_v3_trades": pre_v3[0], "pre_v3_pnl": pre_v3[1],
        "demo_trades": demo, "mt5_equity": mt5['equity'],
        "is_statistically_meaningful": total >= 50,
    }

def print_validation_status():
    s = get_validation_status()
    
    print("=" * 65)
    print("  V3 VALIDATION STATUS")
    print("=" * 65)
    
    # WARNING if not enough data
    if s['v3_closed'] < 50:
        print()
        print("  *** STATISTICAL WARNING ***")
        print(f"  Only {s['v3_closed']} verified trades. Need 50+ for review.")
        print("  Current results are NOT statistically meaningful.")
        print("  Do NOT modify strategy based on <50 trades.")
        print()
    
    print(f"  V3 Verified Closed: {s['v3_closed']}")
    if s['v3_closed'] > 0:
        print(f"  Wins: {s['v3_wins']} | Losses: {s['v3_closed'] - s['v3_wins']}")
        print(f"  Win Rate: {s['v3_wr']:.0f}%", 
              "(NOT meaningful)" if s['v3_closed'] < 50 else "")
        print(f"  Realized P&L: ${s['v3_pnl']:,.2f}")
    print()
    
    print(f"  PRE_V3 (archived): {s['pre_v3_trades']} trades, PnL: ${s['pre_v3_pnl']:,.2f}, PF: 0.65")
    print(f"  PRE_V3 was a LOSING strategy. V3 must prove it is different.")
    print()
    
    if s['demo_trades'] > 0:
        print(f"  Demo (excluded): {s['demo_trades']} trades")
        print()
    
    print("  PROGRESS:")
    milestones = [(10, "Execution"), (25, "Risk"), (50, "Review"), (100, "Statistical"), (300, "Production")]
    for target, label in milestones:
        if s['v3_closed'] >= target:
            print(f"    [DONE] {target} - {label}")
        else:
            pct = s['v3_closed'] / target * 100
            bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
            needed = target - s['v3_closed']
            print(f"    [{bar}] {s['v3_closed']}/{target} {label} (~{needed} more)")
            break
    
    print()
    print("  HONEST VERDICT:")
    if s['v3_closed'] < 10:
        print("  Not enough data. Keep collecting.")
    elif s['v3_closed'] < 50:
        print("  Execution verified. Profitability still unknown.")
    elif s['v3_closed'] < 100:
        print("  Directional evidence emerging. Do not scale yet.")
    else:
        print("  Sufficient data for statistical review.")
    
    print("=" * 65)

if __name__ == "__main__":
    print_validation_status()
