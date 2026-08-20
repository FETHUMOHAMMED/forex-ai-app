"""FINAL PAPER TRADING CRITERIA - Corrected per advisor."""
import json
from pathlib import Path

def define_final_criteria():
    """Define corrected paper trading criteria."""
    
    criteria = {
        "strategy": "V4_CANONICAL_1.0",
        "frozen": True,
        "frozen_date": "2026-08-19",
        
        "sample_requirements": {
            "min_trades": 50,
            "preferred_trades": 75,
            "duration_days": 90
        },
        
        "performance_criteria": {
            "expectancy_positive": True,  # Must be > 0R
            "min_profit_factor": 1.15,
            "directionally_consistent_with_oos": True,
            "oos_reference_expectancy": 0.158,
            "oos_reference_pf": 1.277,
            "note": "Paper expectancy > 0R AND PF > 1.15 AND directionally consistent with OOS"
        },
        
        "drawdown_limits": {
            "warning_level_r": 30.0,
            "review_level_r": 35.0,
            "hard_safety_limit_r": 50.0,
            "note": "30R = warning, 35R = review, 50R = halt. Monte Carlo worst case was 43R."
        },
        
        "operational_requirements": {
            "unauthorized_mt5_executions": 0,
            "cross_account_executions": 0,
            "stale_signal_executions": 0,
            "risk_gate_bypasses": 0,
            "reconciliation_rate": 1.0,
            "evidence_record_rate": 1.0
        },
        
        "consistency_requirements": {
            "no_single_day_dominance": True,
            "no_single_trade_dependence": True,
            "multiple_regimes_tested": True,
            "profitable_weeks_ratio": 0.5
        },
        
        "signal_logging_required": [
            "timestamp",
            "symbol",
            "direction",
            "fvg_detected",
            "bullish_bias",
            "session",
            "atr_regime",
            "spread",
            "signal_decision",
            "reason",
            "entry",
            "sl",
            "tp",
            "risk",
            "strategy_version"
        ],
        
        "trade_logging_required": [
            "signal_id",
            "order_ticket",
            "position_ticket",
            "deal_ticket",
            "planned_entry",
            "actual_entry",
            "planned_sl",
            "actual_sl",
            "planned_tp",
            "actual_tp",
            "pnl_r",
            "pnl_usd",
            "mae",
            "mfe",
            "execution_slippage",
            "spread_at_entry",
            "reconciliation_status"
        ]
    }
    
    print("="*70)
    print("  FINAL PAPER TRADING CRITERIA (CORRECTED)")
    print("="*70)
    
    print(f"\n  Strategy: {criteria['strategy']}")
    print(f"  Frozen: {criteria['frozen']}")
    print(f"  Frozen Date: {criteria['frozen_date']}")
    
    print(f"\n  SAMPLE REQUIREMENTS:")
    print(f"    Min trades: {criteria['sample_requirements']['min_trades']}")
    print(f"    Preferred: {criteria['sample_requirements']['preferred_trades']}")
    print(f"    Duration: {criteria['sample_requirements']['duration_days']} days")
    
    print(f"\n  PERFORMANCE CRITERIA (CORRECTED):")
    print(f"    Expectancy: > 0R (NOT hard interval)")
    print(f"    PF: > {criteria['performance_criteria']['min_profit_factor']}")
    print(f"    OOS reference: {criteria['performance_criteria']['oos_reference_expectancy']}R")
    print(f"    Note: {criteria['performance_criteria']['note']}")
    
    print(f"\n  DRAWDOWN LIMITS (CORRECTED):")
    print(f"    Warning: {criteria['drawdown_limits']['warning_level_r']}R")
    print(f"    Review: {criteria['drawdown_limits']['review_level_r']}R")
    print(f"    Hard halt: {criteria['drawdown_limits']['hard_safety_limit_r']}R")
    print(f"    Note: {criteria['drawdown_limits']['note']}")
    
    print(f"\n  SIGNAL LOGGING (EVERY signal, even NO_TRADE):")
    for field in criteria['signal_logging_required']:
        print(f"    - {field}")
    
    print(f"\n  TRADE LOGGING (every executed trade):")
    for field in criteria['trade_logging_required']:
        print(f"    - {field}")
    
    # Save
    filepath = Path("research/paper_criteria_final.json")
    with open(filepath, 'w') as f:
        json.dump(criteria, f, indent=2)
    
    print(f"\n  Criteria saved to {filepath}")
    
    return criteria

if __name__ == "__main__":
    criteria = define_final_criteria()
