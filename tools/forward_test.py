"""Forward testing framework for the promising H4 strategy."""
import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
from pathlib import Path

def setup_forward_test():
    """Setup forward testing for the H4 strategy."""
    print("="*60)
    print("  FORWARD TESTING SETUP")
    print("="*60)
    
    # Strategy parameters (from backtest)
    strategy_params = {
        "name": "USDJPY_H4_TREND",
        "timeframe": "H4",
        "symbol": "USDJPYm",
        "ema_fast": 20,
        "ema_medium": 50,
        "ema_slow": 200,
        "rsi_period": 14,
        "rsi_threshold_long": 50,
        "rsi_threshold_short": 50,
        "sl_atr_mult": 2.0,
        "tp_atr_mult": 4.0,
        "max_hold_bars": 20,
        "backtest_results": {
            "trades": 24,
            "win_rate": 0.625,
            "profit_factor": 1.734,
            "expectancy": 0.275,
            "max_drawdown": -7.0
        }
    }
    
    # Save strategy for forward testing
    forward_test_config = {
        "strategy": strategy_params,
        "start_date": datetime.now().isoformat(),
        "duration_days": 60,
        "min_trades_needed": 30,
        "monitoring": {
            "check_interval_hours": 4,
            "alert_if": {
                "drawdown_exceeds": -5.0,
                "consecutive_losses": 5,
                "profit_factor_below": 1.2
            }
        },
        "success_criteria": {
            "min_trades": 30,
            "min_profit_factor": 1.3,
            "min_expectancy": 0.2,
            "max_drawdown": -10.0
        }
    }
    
    # Save configuration
    Path("research/forward_test").mkdir(parents=True, exist_ok=True)
    with open("research/forward_test/config.json", "w") as f:
        import json
        json.dump(forward_test_config, f, indent=2)
    
    print(f"\nStrategy: {strategy_params['name']}")
    print(f"Backtest results:")
    print(f"  24 trades, 62.5% win, PF 1.734, +0.275R expectancy")
    print(f"\nForward test configuration saved")
    print(f"Duration: 60 days")
    print(f"Target: 30+ trades")
    print(f"Success criteria:")
    print(f"  PF > 1.3")
    print(f"  Expectancy > 0.2R")
    print(f"  Max DD < -10R")
    
    print(f"\n{'='*60}")
    print("  RECOMMENDED ACTIONS")
    print("="*60)
    print("""
1. Run this strategy on DEMO account for 60 days
2. Record every trade with full details
3. Compare forward results with backtest
4. If results hold up:
   - Fund account with at least $500
   - Start with minimum position size
   - Scale up slowly
5. If results degrade:
   - Strategy was overfit
   - Return to research phase
   - Test new hypotheses
""")
    
    return forward_test_config

if __name__ == "__main__":
    setup_forward_test()
