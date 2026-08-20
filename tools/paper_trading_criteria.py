"""PAPER TRADING SUCCESS CRITERIA - Defined before starting."""
import json
from pathlib import Path

def define_paper_trading_criteria():
    """Define success criteria BEFORE paper trading."""
    
    criteria = {
        "sample_requirements": {
            "min_trades": 50,
            "preferred_trades": 75,
            "duration_days": 90,
            "min_trades_per_month": 15
        },
        
        "performance_criteria": {
            "min_expectancy_r": 0.0,  # Must be positive
            "min_profit_factor": 1.15,
            "max_drawdown_r": 30.0,
            "close_to_oos_expectation": True,  # ~0.15R
            "oos_expectation_range": (0.05, 0.25)  # Acceptable range
        },
        
        "operational_requirements": {
            "unauthorized_mt5_executions": 0,
            "cross_account_executions": 0,
            "stale_signal_executions": 0,
            "risk_gate_bypasses": 0,
            "reconciliation_rate": 1.0,  # 100%
            "evidence_record_rate": 1.0  # 100%
        },
        
        "consistency_requirements": {
            "no_single_day_dominance": True,  # No day > 30% of profits
            "no_single_trade_dependence": True,  # No trade > 40% of profits
            "multiple_regimes_tested": True,
            "profitable_weeks_ratio": 0.5  # At least 50% profitable weeks
        },
        
        "go_live_criteria": {
            "all_sample_requirements_met": True,
            "all_performance_criteria_met": True,
            "all_operational_requirements_met": True,
            "all_consistency_requirements_met": True,
            "capital_available": 2000,
            "risk_per_trade": 0.25
        }
    }
    
    print("="*70)
    print("  PAPER TRADING SUCCESS CRITERIA")
    print("="*70)
    
    print(f"\n  SAMPLE REQUIREMENTS:")
    print(f"    Min trades: {criteria['sample_requirements']['min_trades']}")
    print(f"    Preferred: {criteria['sample_requirements']['preferred_trades']}")
    print(f"    Duration: {criteria['sample_requirements']['duration_days']} days")
    
    print(f"\n  PERFORMANCE CRITERIA:")
    print(f"    Expectancy: > {criteria['performance_criteria']['min_expectancy_r']}R")
    print(f"    PF: > {criteria['performance_criteria']['min_profit_factor']}")
    print(f"    Max DD: < {criteria['performance_criteria']['max_drawdown_r']}R")
    print(f"    Close to OOS: {criteria['performance_criteria']['oos_expectation_range']}R")
    
    print(f"\n  OPERATIONAL REQUIREMENTS:")
    for key, value in criteria['operational_requirements'].items():
        print(f"    {key.replace('_', ' ').title()}: {value}")
    
    print(f"\n  CONSISTENCY REQUIREMENTS:")
    for key, value in criteria['consistency_requirements'].items():
        print(f"    {key.replace('_', ' ').title()}: {value}")
    
    # Save criteria
    filepath = Path("research/paper_trading_criteria.json")
    with open(filepath, 'w') as f:
        json.dump(criteria, f, indent=2)
    
    print(f"\n  Criteria saved to {filepath}")
    print(f"\n{'='*70}")
    print("  GO LIVE CHECKLIST")
    print("="*70)
    print("""
  Only proceed to live trading if ALL of these are TRUE:
  
  ? 50+ paper trades completed
  ? Expectancy > 0R
  ? PF > 1.15
  ? Max DD < 30R
  ? Zero safety violations
  ? 100% reconciliation
  ? 100% evidence records
  ? No single day > 30% of profits
  ? No single trade > 40% of profits
  ? $2,000+ capital available
""")
    
    return criteria

if __name__ == "__main__":
    criteria = define_paper_trading_criteria()
