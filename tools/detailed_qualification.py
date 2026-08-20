"""Detailed Qualification - Every gate shows full evidence + Execution vs Strategy separation."""
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

class ExecutionQualification:
    """A. Was this trade EXECUTED correctly?"""
    
    def __init__(self, trade: dict):
        self.trade = trade
        self.checks = {}
    
    def evaluate(self):
        t = self.trade
        direction = t.get('signal')
        actual_entry = t.get('actual_entry') or t.get('entry')
        actual_sl = t.get('actual_sl') or t.get('stop_loss')
        actual_tp = t.get('actual_tp') or t.get('take_profit')
        volume = t.get('volume')
        
        # 1. Signal freshness
        age = t.get('signal_age_ms')
        self.checks['signal_fresh'] = {
            'passed': age is not None and age < 120000,
            'evidence': f"Signal age: {age}ms" if age is not None else "Signal age: UNKNOWN",
            'max': "120000ms (120s)"
        }
        
        # 2. Entry deviation
        deviation = t.get('entry_deviation_pips')
        self.checks['entry_deviation_ok'] = {
            'passed': deviation is not None and abs(deviation) <= 5.0,
            'evidence': f"Deviation: {deviation} pips" if deviation is not None else "Deviation: UNKNOWN",
            'max': "5.0 pips"
        }
        
        # 3. SL valid
        if direction and actual_entry and actual_sl:
            sl_valid = actual_sl > actual_entry if direction == 'SELL' else actual_sl < actual_entry
            self.checks['sl_valid'] = {
                'passed': sl_valid,
                'evidence': f"SL={actual_sl} vs Entry={actual_entry} ({direction})",
                'expected': "SL above entry" if direction == 'SELL' else "SL below entry"
            }
        else:
            self.checks['sl_valid'] = {
                'passed': False,
                'evidence': "Missing SL or entry",
                'expected': "Complete SL data"
            }
        
        # 4. TP valid
        if direction and actual_entry and actual_tp:
            tp_valid = actual_tp < actual_entry if direction == 'SELL' else actual_tp > actual_entry
            self.checks['tp_valid'] = {
                'passed': tp_valid,
                'evidence': f"TP={actual_tp} vs Entry={actual_entry} ({direction})",
                'expected': "TP below entry" if direction == 'SELL' else "TP above entry"
            }
        else:
            self.checks['tp_valid'] = {
                'passed': False,
                'evidence': "Missing TP or entry",
                'expected': "Complete TP data"
            }
        
        # 5. Spread
        spread = t.get('spread_at_execution')
        self.checks['spread_ok'] = {
            'passed': spread is not None and spread <= 0.0015,
            'evidence': f"Spread: {spread}" if spread is not None else "Spread: UNKNOWN",
            'max': "0.0015 (15 pips)"
        }
        
        # 6. Risk
        risk_budget = t.get('risk_budget_usd')
        actual_risk = t.get('actual_risk_usd')
        if actual_entry and actual_sl and volume:
            sl_distance = abs(actual_entry - actual_sl) / 0.0001
            estimated_risk = sl_distance * 10.0 * volume
            self.checks['risk_ok'] = {
                'passed': risk_budget is not None and estimated_risk <= risk_budget * 1.01,
                'evidence': f"Risk: ${estimated_risk:.2f} (SL {sl_distance:.1f} pips)",
                'budget': f"${risk_budget:.4f}" if risk_budget else "UNKNOWN"
            }
        else:
            self.checks['risk_ok'] = {
                'passed': False,
                'evidence': "Cannot calculate risk - missing entry/SL/volume",
                'budget': "UNKNOWN"
            }
        
        # 7. MT5 position
        mt5_pos = t.get('mt5_position_id')
        self.checks['mt5_position'] = {
            'passed': mt5_pos is not None,
            'evidence': f"Position: {mt5_pos}" if mt5_pos else "No MT5 position"
        }
        
        # 8. MT5 reconciliation
        pnl = t.get('pnl')
        contract_valid = t.get('execution_contract_valid', 0)
        self.checks['mt5_reconciled'] = {
            'passed': pnl is not None and contract_valid == 1,
            'evidence': f"PnL: {pnl}, Contract Valid: {contract_valid}"
        }
        
        # 9. Account
        self.checks['account_correct'] = {
            'passed': t.get('account') == 'Live_Micro' and t.get('account_name') == 'Live_Micro',
            'evidence': f"Account: {t.get('account')}/{t.get('account_name')}"
        }
        
        # 10. Timestamps
        entry_ts = t.get('timestamp')
        exit_ts = t.get('exit_time')
        self.checks['timestamp_valid'] = {
            'passed': entry_ts is not None and (exit_ts is None or exit_ts >= entry_ts),
            'evidence': f"Entry: {entry_ts}, Exit: {exit_ts}"
        }
        
        return all(c['passed'] for c in self.checks.values())


class StrategyQualification:
    """B. Can this trade evaluate V3_REGIME?"""
    
    def __init__(self, trade: dict, execution_passed: bool):
        self.trade = trade
        self.execution_passed = execution_passed
        self.checks = {}
    
    def evaluate(self):
        t = self.trade
        
        # Strategy qualification requires execution to pass first
        self.checks['execution_contract_valid'] = {
            'passed': self.execution_passed,
            'evidence': "Execution qualification must pass first"
        }
        
        # Closed
        result = t.get('result')
        self.checks['closed'] = {
            'passed': result in ('WIN', 'LOSS', 'BREAKEVEN'),
            'evidence': f"Result: {result}"
        }
        
        # Valid PnL
        pnl = t.get('pnl')
        self.checks['valid_pnl'] = {
            'passed': pnl is not None,
            'evidence': f"PnL: ${pnl:.2f}" if pnl is not None else "PnL: None"
        }
        
        # Correct strategy
        self.checks['correct_strategy'] = {
            'passed': t.get('strategy_version') == 'V3_REGIME',
            'evidence': f"Strategy: {t.get('strategy_version')}"
        }
        
        # Correct account
        self.checks['correct_account'] = {
            'passed': t.get('account') == 'Live_Micro',
            'evidence': f"Account: {t.get('account')}"
        }
        
        return all(c['passed'] for c in self.checks.values())


def print_detailed_qualification(trade_id: int):
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    c.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    row = c.fetchone()
    if not row:
        print(f"Trade {trade_id} not found")
        return
    cols = [d[0] for d in c.description]
    t = dict(zip(cols, row))
    conn.close()
    
    print("=" * 70)
    print(f"  DETAILED QUALIFICATION - ID {trade_id}")
    print("=" * 70)
    
    # EXECUTION QUALIFICATION
    print(f"\n  A. EXECUTION QUALIFICATION (executed correctly?)")
    print(f"  {'-'*50}")
    eq = ExecutionQualification(t)
    exec_passed = eq.evaluate()
    for check, result in eq.checks.items():
        icon = "PASS" if result['passed'] else "FAIL"
        print(f"    [{icon}] {check}")
        print(f"         Evidence: {result['evidence']}")
        if 'max' in result: print(f"         Max: {result['max']}")
        if 'budget' in result: print(f"         Budget: {result['budget']}")
        if 'expected' in result: print(f"         Expected: {result['expected']}")
    
    print(f"\n  Execution Qualified: {'YES' if exec_passed else 'NO'}")
    
    # STRATEGY QUALIFICATION
    print(f"\n  B. STRATEGY QUALIFICATION (usable for V3 evaluation?)")
    print(f"  {'-'*50}")
    sq = StrategyQualification(t, exec_passed)
    strat_passed = sq.evaluate()
    for check, result in sq.checks.items():
        icon = "PASS" if result['passed'] else "FAIL"
        print(f"    [{icon}] {check}")
        print(f"         Evidence: {result['evidence']}")
    
    print(f"\n  Strategy Qualified: {'YES' if strat_passed else 'NO'}")
    print(f"  FINAL: {'QUALIFIED' if exec_passed and strat_passed else 'NOT QUALIFIED'}")
    print("=" * 70)
    return exec_passed and strat_passed

if __name__ == "__main__":
    for tid in [163, 164]:
        print_detailed_qualification(tid)
        print()
