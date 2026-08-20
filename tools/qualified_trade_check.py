"""DEFINITIVE Qualified Trade Check - Every gate must be verified."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

def check_qualified_trade(trade_id: int) -> dict:
    """
    THE definitive check. Every gate must PASS with evidence.
    Returns complete qualification result.
    """
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    c.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    row = c.fetchone()
    if not row:
        return {"qualified": False, "reason": f"Trade {trade_id} not found"}
    
    cols = [d[0] for d in c.description]
    t = dict(zip(cols, row))
    conn.close()
    
    checks = {}
    
    # 1. FRESH SIGNAL (historical audit: compare signal time vs execution time)
    signal_age_ms = t.get('signal_age_ms')
    
    if signal_age_ms is not None:
        # New code: signal_age_ms is stored directly
        checks['fresh_signal'] = signal_age_ms < 120000
    else:
        # Historical trade: calculate from timestamps if available
        signal_ts = t.get('signal_timestamp') or t.get('planned_entry_time')
        execution_ts = t.get('timestamp')  # This is the DB entry time = execution time
        
        if signal_ts and execution_ts:
            from datetime import datetime as dt
            try:
                signal_time = dt.fromisoformat(str(signal_ts).replace('Z', '+00:00'))
                exec_time = dt.fromisoformat(str(execution_ts).replace('Z', '+00:00'))
                age_seconds = (exec_time - signal_time).total_seconds()
                checks['fresh_signal'] = age_seconds < 120
            except:
                checks['fresh_signal'] = False
        else:
            # Cannot determine freshness = UNVERIFIED (not FAIL)
            checks['fresh_signal'] = None
    
    # 2. CORRECT ACCOUNT
    checks['correct_account'] = (
        t.get('account') == 'Live_Micro' and
        t.get('account_name') == 'Live_Micro' and
        t.get('account_id') == REDACTED_LIVE_ACCOUNT
    )
    
    # 3. CORRECT SYMBOL (normalized)
    pair = t.get('pair', '')
    checks['correct_symbol'] = pair == 'EURUSD' or pair == 'EURUSDm'
    
    # 4. CORRECT DIRECTION
    checks['correct_direction'] = t.get('signal') in ('BUY', 'SELL')
    
    # 5. VALID ENTRY
    entry = t.get('actual_entry') or t.get('entry')
    checks['valid_entry'] = entry is not None and entry > 0
    
    # 6. VALID SL
    sl = t.get('actual_sl') or t.get('stop_loss')
    direction = t.get('signal')
    if entry and sl and direction:
        checks['valid_sl'] = sl > entry if direction == 'SELL' else sl < entry
    else:
        checks['valid_sl'] = False
    
    # 7. VALID TP
    tp = t.get('actual_tp') or t.get('take_profit')
    if entry and tp and direction:
        checks['valid_tp'] = tp < entry if direction == 'SELL' else tp > entry
    else:
        checks['valid_tp'] = False
    
    # 8. VALID SPREAD (UNVERIFIED if no telemetry)
    spread = t.get('spread_at_execution')
    if spread is not None:
        checks['valid_spread'] = spread <= 0.0015
    else:
        checks['valid_spread'] = None  # UNVERIFIED - no historical telemetry
    
    # 9. VALID RISK (UNVERIFIED if no telemetry)
    risk_budget = t.get('risk_budget_usd')
    actual_risk = t.get('actual_risk_usd')
    if risk_budget is not None and actual_risk is not None:
        checks['valid_risk'] = actual_risk <= risk_budget * 1.01
    else:
        checks['valid_risk'] = None  # UNVERIFIED - no risk snapshot
    
    # 10. VALID VOLUME
    volume = t.get('volume')
    checks['valid_volume'] = volume is not None and 0 < volume <= 0.01
    
    # 11. MT5 POSITION EXISTS
    checks['mt5_position'] = t.get('mt5_position_id') is not None
    
    # 12. RECONCILED (call canonical reconciler, not stored field)
    if t.get('mt5_position_id') is not None:
        try:
            from packages.execution.mt5_reconciler import resolve_trade_identity
            lineage = resolve_trade_identity(t['mt5_position_id'])
            if lineage and lineage.is_complete:
                # Check PnL matches
                if t.get('pnl') is not None and lineage.net_pnl is not None:
                    checks['reconciled'] = abs(t['pnl'] - lineage.net_pnl) < 0.01
                else:
                    checks['reconciled'] = False
            else:
                checks['reconciled'] = False
        except Exception as e:
            checks['reconciled'] = False
    else:
        checks['reconciled'] = False
    
    # 13. TIMESTAMPS VALID
    entry_ts = t.get('timestamp')
    exit_ts = t.get('exit_time')
    checks['timestamps_valid'] = entry_ts is not None and (exit_ts is None or exit_ts >= entry_ts)
    
    # 14. CLOSED
    checks['closed'] = t.get('result') in ('WIN', 'LOSS', 'BREAKEVEN')
    
    # Only count actual FAILs (not UNVERIFIED)
    failed = [k for k, v in checks.items() if v is False]
    unverified = [k for k, v in checks.items() if v is None]
    all_pass = len(failed) == 0 and len(unverified) == 0
    
    return {
        "qualified": all_pass,
        "checks": checks,
        "failed_checks": failed,
        "unverified_checks": unverified,
        "trade_id": trade_id,
    }

def print_qualification(trade_id: int):
    """Print definitive qualification report."""
    result = check_qualified_trade(trade_id)
    
    print("=" * 70)
    print(f"  DEFINITIVE QUALIFIED TRADE CHECK - ID {trade_id}")
    print("=" * 70)
    
    print(f"\n  CHECKS:")
    for check, passed in result.get("checks", {}).items():
        if passed is True:
            icon = "PASS"
        elif passed is False:
            icon = "FAIL"
        else:
            icon = "UNVERIFIED"
        print(f"    [{icon}] {check}")
    
    if result.get("failed_checks"):
        print(f"\n  FAILED: {result['failed_checks']}")
    
    print(f"\n  QUALIFIED: {'YES - 1/10 EXECUTION INTEGRITY' if result['qualified'] else 'NO'}")
    if not result['qualified'] and result.get('reason'):
        print(f"  REASON: {result['reason']}")
    print("=" * 70)
    
    return result

if __name__ == "__main__":
    # Check all V3 trades to see if any qualify
    print("  CHECKING ALL V3 TRADES FOR QUALIFICATION\n")
    
    for tid in [163, 164, 165]:
        print_qualification(tid)
        print()
