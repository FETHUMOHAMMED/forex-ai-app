"""Qualified Trade Tracker v2 - Complete qualification with ALL criteria enforced."""
import sqlite3
from datetime import datetime, timezone

def get_trade_qualification(trade_id: int) -> dict:
    """Get complete qualification for one trade with ALL criteria"""
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    row = c.fetchone()
    if not row:
        return None
    
    cols = [d[0] for d in c.description]
    t = dict(zip(cols, row))
    conn.close()
    
    # === COMPLETE QUALIFICATION CHECKS ===
    checks = {}
    
    # 1. Fresh signal (must have signal_age_ms < 120000)
    signal_age = t.get('signal_age_ms')
    checks['fresh_signal'] = signal_age is not None and signal_age < 120000
    
    # 2. Entry deviation <= 5 pips
    deviation = t.get('entry_deviation_pips')
    checks['entry_deviation_ok'] = deviation is not None and abs(deviation) <= 5.0
    
    # 3. SL must be valid (correct side of actual entry for direction)
    direction = t.get('signal')
    actual_entry = t.get('actual_entry') or t.get('entry')
    actual_sl = t.get('actual_sl') or t.get('stop_loss')
    if actual_entry and actual_sl and direction:
        if direction == 'SELL':
            checks['valid_sl'] = actual_sl > actual_entry
        else:
            checks['valid_sl'] = actual_sl < actual_entry
    else:
        checks['valid_sl'] = False
    
    # 4. TP must be valid
    actual_tp = t.get('actual_tp') or t.get('take_profit')
    if actual_entry and actual_tp and direction:
        if direction == 'SELL':
            checks['valid_tp'] = actual_tp < actual_entry
        else:
            checks['valid_tp'] = actual_tp > actual_entry
    else:
        checks['valid_tp'] = False
    
    # 5. Spread check (must have spread_at_execution)
    spread = t.get('spread_at_execution')
    checks['spread_ok'] = spread is not None and spread <= 0.0015
    
    # 6. Volume <= 0.01
    volume = t.get('volume')
    checks['volume_ok'] = volume is not None and volume <= 0.01
    
    # 7. Risk budget check
    risk_budget = t.get('risk_budget_usd')
    actual_risk = t.get('actual_risk_usd')
    if risk_budget is not None and actual_risk is not None:
        checks['risk_ok'] = actual_risk <= risk_budget * 1.01
    else:
        checks['risk_ok'] = False  # FAIL CLOSED - unknown risk = not qualified
    
    # 8. MT5 position verified
    checks['mt5_position'] = t.get('mt5_position_id') is not None
    
    # 9. Reconciled (PnL matches MT5)
    checks['reconciled'] = t.get('pnl') is not None and t.get('execution_contract_valid', 0) == 1
    
    # 10. Timestamps valid
    entry_ts = t.get('timestamp')
    exit_ts = t.get('exit_time')
    if entry_ts and exit_ts:
        checks['timestamp_ok'] = exit_ts >= entry_ts
    elif entry_ts:
        checks['timestamp_ok'] = True
    else:
        checks['timestamp_ok'] = False
    
    # 11. Account correct
    checks['account_ok'] = t.get('account') == 'Live_Micro' and t.get('account_name') == 'Live_Micro'
    
    # 12. Must be CLOSED (has result)
    checks['closed'] = t.get('result') in ('WIN', 'LOSS', 'BREAKEVEN')
    
    # ALL must pass
    checks['qualified'] = all(checks.values())
    
    return checks

def print_qualification(trade_id: int):
    checks = get_trade_qualification(trade_id)
    if not checks:
        print(f"Trade {trade_id} not found")
        return
    
    print("=" * 65)
    print(f"  QUALIFICATION - ID {trade_id}")
    print("=" * 65)
    
    failed = []
    for check, passed in checks.items():
        if check == 'qualified':
            continue
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {check}")
        if not passed:
            failed.append(check)
    
    print(f"\n  QUALIFIED: {'YES' if checks['qualified'] else 'NO'}")
    if failed:
        print(f"  Failed: {len(failed)} checks")
    print("=" * 65)
    return checks

if __name__ == "__main__":
    for tid in [163, 164]:
        print_qualification(tid)
        print()
