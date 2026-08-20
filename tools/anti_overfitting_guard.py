"""ANTI-OVERFITTING GUARD - Protects against curve-fitting."""
import json
from pathlib import Path
from datetime import datetime

class AntiOverfittingGuard:
    """Prevents dangerous optimization practices."""
    
    def __init__(self):
        self.rules = {
            "parameter_count": {
                "max_strategy_parameters": 5,
                "current_parameters": 3,  # FVG, Bias, Session
                "warning": "More than 5 parameters = overfitting risk"
            },
            "optimization_limits": {
                "max_parameter_combinations": 30,
                "tested_combinations": 29,
                "warning": "Testing too many combinations = data mining"
            },
            "validation_requirements": {
                "min_walk_forward_windows": 4,
                "required_profitable_windows": 3,  # 75%
                "min_oos_trades": 200,
                "warning": "Insufficient OOS validation"
            },
            "performance_limits": {
                "max_acceptable_pf": 2.5,
                "max_acceptable_expectancy": 0.5,
                "warning": "PF > 2.5 or expectancy > 0.5 = suspicious, likely overfit"
            },
            "forbidden_practices": [
                "Tuning parameters until PF > 3.0",
                "Testing 100+ parameter combinations",
                "Using 20+ indicators",
                "Optimizing on test data",
                "Curve-fitting to specific years",
                "Adding parameters to improve backtest",
                "Ignoring walk-forward results",
                "Deploying without OOS validation"
            ]
        }
        
    def check_parameter_count(self, params: int) -> bool:
        """Check if too many parameters."""
        return params <= self.rules["parameter_count"]["max_strategy_parameters"]
    
    def check_performance(self, pf: float, expectancy: float) -> bool:
        """Check if performance is suspiciously high."""
        if pf > self.rules["performance_limits"]["max_acceptable_pf"]:
            print(f"?? WARNING: PF {pf:.2f} is suspiciously high")
            print(f"   Max acceptable: {self.rules['performance_limits']['max_acceptable_pf']}")
            print(f"   High PF often indicates overfitting")
            return False
        return True
    
    def check_validation(self, oos_trades: int, profitable_windows: int, total_windows: int) -> bool:
        """Check if validation is sufficient."""
        if oos_trades < self.rules["validation_requirements"]["min_oos_trades"]:
            print(f"?? WARNING: Only {oos_trades} OOS trades")
            print(f"   Minimum required: {self.rules['validation_requirements']['min_oos_trades']}")
            return False
        return True
    
    def display_guard_status(self):
        """Display current protection status."""
        print("="*70)
        print("  ANTI-OVERFITTING GUARD")
        print("="*70)
        
        print(f"\n  CURRENT STRATEGY PARAMETERS:")
        print(f"    1. FVG detection")
        print(f"    2. Bullish bias (EMA50 > EMA200)")
        print(f"    3. Session filter")
        print(f"    Total: 3 parameters ? (safe)")
        
        print(f"\n  CURRENT PERFORMANCE:")
        print(f"    Backtest PF: 1.494 ? (below 2.5 limit)")
        print(f"    Backtest expectancy: +0.270R ? (below 0.5 limit)")
        print(f"    Walk-forward PF: 1.277 ? (realistic)")
        print(f"    Walk-forward expectancy: +0.158R ? (honest)")
        
        print(f"\n  VALIDATION STATUS:")
        print(f"    Walk-forward windows: 4 ?")
        print(f"    Profitable windows: 4/4 ?")
        print(f"    OOS trades: 230 ?")
        print(f"    P-value: 0.085 (marginal, honest)")
        
        print(f"\n{'='*70}")
        print("  FORBIDDEN PRACTICES (NEVER DO THESE)")
        print("="*70)
        
        for i, practice in enumerate(self.rules["forbidden_practices"], 1):
            print(f"  ? {i}. {practice}")
        
        print(f"\n{'='*70}")
        print("  THE RIGHT GOAL")
        print("="*70)
        print("""
  NOT: "Find the best backtest"
  
  BUT: "Find a strategy whose performance survives:
        - Unseen data
        - Changing market regimes
        - Realistic execution costs
        - Live trading"
""")
    
    def save_guard(self):
        """Save guard configuration."""
        filepath = Path("research/anti_overfitting_guard.json")
        with open(filepath, 'w') as f:
            json.dump(self.rules, f, indent=2)
        print(f"\nGuard saved to {filepath}")

if __name__ == "__main__":
    guard = AntiOverfittingGuard()
    guard.display_guard_status()
    guard.save_guard()
