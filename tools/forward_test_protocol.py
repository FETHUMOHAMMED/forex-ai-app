"""Forward testing protocol for validated strategy."""
import json
from datetime import datetime, timedelta
from pathlib import Path

def create_forward_test_plan():
    """Create detailed forward testing plan."""
    plan = {
        "strategy": {
            "name": "FVG_H4_2.5R_London",
            "pair": "USDJPYm",
            "timeframe": "H4",
            "entry": "Fair Value Gap",
            "session": "London (7-11 UTC)",
            "rr_ratio": 2.5,
            "sl_atr_mult": 1.5,
            "tp_atr_mult": 3.75,
            "max_hold_bars": 50
        },
        "backtest_validation": {
            "period": "2018-2026 (8 years)",
            "trades": 138,
            "win_rate": 0.406,
            "profit_factor": 1.637,
            "expectancy": 0.378,
            "max_drawdown": -7.0,
            "p_value": 0.0096,
            "out_of_sample_pf": 1.315
        },
        "forward_test": {
            "duration_days": 60,
            "target_trades": 20,
            "account_type": "DEMO",
            "initial_balance": 10000,
            "risk_per_trade_pct": 0.5,
            "success_criteria": {
                "min_trades": 15,
                "min_profit_factor": 1.3,
                "min_expectancy": 0.2,
                "max_drawdown": -10.0
            }
        },
        "monitoring": {
            "check_frequency": "Daily",
            "record_fields": [
                "entry_time", "entry_price", "stop_loss", "take_profit",
                "exit_time", "exit_price", "result", "r_multiple"
            ],
            "alert_thresholds": {
                "consecutive_losses": 4,
                "drawdown_warning": -5.0,
                "drawdown_critical": -10.0
            }
        },
        "go_live_criteria": {
            "forward_test_passed": True,
            "min_account_balance": 2000,
            "max_risk_per_trade": 10,
            "position_size_formula": "risk_amount / (sl_distance * pip_value)"
        }
    }
    
    # Save plan
    Path("research/forward_test").mkdir(parents=True, exist_ok=True)
    with open("research/forward_test/plan.json", "w") as f:
        json.dump(plan, f, indent=2)
    
    print("="*60)
    print("  FORWARD TESTING PLAN CREATED")
    print("="*60)
    print(f"\nStrategy: {plan['strategy']['name']}")
    print(f"Backtest: {plan['backtest_validation']['trades']} trades over 8 years")
    print(f"Expectancy: +{plan['backtest_validation']['expectancy']}R")
    print(f"Statistical significance: p = {plan['backtest_validation']['p_value']}")
    
    print(f"\nForward Test:")
    print(f"  Duration: 60 days")
    print(f"  Target: 20+ trades")
    print(f"  Account: DEMO ($10,000 virtual)")
    print(f"  Risk per trade: 0.5%")
    
    print(f"\nGo Live Requirements:")
    print(f"  1. Forward test passes all criteria")
    print(f"  2. Minimum $2,000 account balance")
    print(f"  3. Maximum $10 risk per trade")
    
    print(f"\n{'='*60}")
    print("  ACTION ITEMS")
    print("="*60)
    print("""
1. Set up DEMO account with $10,000 virtual balance
2. Configure MT5 for automated trading
3. Run strategy in forward test mode
4. Record every trade with full details
5. Review results daily
6. After 60 days, compare with backtest
7. If criteria met, prepare for live deployment
""")
    
    return plan

if __name__ == "__main__":
    create_forward_test_plan()
