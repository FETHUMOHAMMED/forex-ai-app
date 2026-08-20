"""STRATEGY RESEARCH ENGINE - Institutional Grade Pipeline."""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timezone
import json
from pathlib import Path
from enum import Enum

class StrategyStatus(Enum):
    HYPOTHESIS = "HYPOTHESIS"
    BACKTESTED = "BACKTESTED"
    CANDIDATE = "CANDIDATE"
    PAPER_VALIDATED = "PAPER_VALIDATED"
    LIVE_VALIDATION = "LIVE_VALIDATION"
    PRODUCTION_APPROVED = "PRODUCTION_APPROVED"
    REJECTED = "REJECTED"

@dataclass
class ValidationCriteria:
    """Minimum thresholds for strategy promotion."""
    min_trades: int = 100
    min_profit_factor: float = 1.3
    min_expectancy_r: float = 0.2
    max_drawdown_pct: float = 15.0
    min_oos_pf: float = 1.2
    min_walk_forward_pf: float = 1.2
    max_monte_carlo_95_dd: float = 20.0
    max_calibration_error: float = 0.15
    min_robustness_score: float = 0.6  # 60% of parameter variations profitable

class StrategyScorecard:
    """Automated scorecard for strategy evaluation."""
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self.metrics = {}
        self.checks = {}
        self.status = StrategyStatus.HYPOTHESIS
        
    def add_metric(self, name: str, value: float):
        """Add a performance metric."""
        self.metrics[name] = value
        
    def run_validation(self, criteria: ValidationCriteria):
        """Run all validation checks."""
        
        # Data integrity
        self.checks["data_integrity"] = self.metrics.get("data_integrity", False)
        
        # Minimum trades
        self.checks["min_trades"] = self.metrics.get("trades", 0) >= criteria.min_trades
        
        # Profit factor
        self.checks["profit_factor"] = self.metrics.get("profit_factor", 0) >= criteria.min_profit_factor
        
        # Expectancy
        self.checks["expectancy"] = self.metrics.get("expectancy_r", 0) >= criteria.min_expectancy_r
        
        # Drawdown
        self.checks["max_drawdown"] = self.metrics.get("max_drawdown_pct", 100) <= criteria.max_drawdown_pct
        
        # Out-of-sample
        self.checks["oos"] = self.metrics.get("oos_pf", 0) >= criteria.min_oos_pf
        
        # Walk-forward
        self.checks["walk_forward"] = self.metrics.get("walk_forward_pf", 0) >= criteria.min_walk_forward_pf
        
        # Monte Carlo
        self.checks["monte_carlo"] = self.metrics.get("mc_95_dd", 100) <= criteria.max_monte_carlo_95_dd
        
        # Calibration
        self.checks["calibration"] = self.metrics.get("calibration_error", 1.0) <= criteria.max_calibration_error
        
        # Robustness
        self.checks["robustness"] = self.metrics.get("robustness_score", 0) >= criteria.min_robustness_score
        
        # Execution feasibility
        self.checks["execution"] = self.metrics.get("execution_feasible", False)
        
        # Risk constraints
        self.checks["risk"] = self.metrics.get("risk_compliant", False)
        
        # Determine status
        passed = sum(1 for check in self.checks.values() if check)
        total = len(self.checks)
        
        if passed == total:
            self.status = StrategyStatus.CANDIDATE
        elif passed >= total - 2:
            self.status = StrategyStatus.BACKTESTED
        else:
            self.status = StrategyStatus.REJECTED
        
        return self.status
    
    def generate_scorecard(self):
        """Generate formatted scorecard."""
        print(f"\n{'='*70}")
        print(f"  STRATEGY SCORECARD")
        print(f"{'='*70}")
        print(f"\n  Strategy: {self.strategy_name}")
        print(f"  Status: {self.status.value}")
        
        print(f"\n  PERFORMANCE METRICS:")
        print(f"  " + "-"*50)
        for name, value in self.metrics.items():
            print(f"    {name}: {value}")
        
        print(f"\n  VALIDATION CHECKS:")
        print(f"  " + "-"*50)
        for check, passed in self.checks.items():
            status = "PASS" if passed else "FAIL"
            print(f"    [{status}] {check}")
        
        passed = sum(1 for check in self.checks.values() if check)
        total = len(self.checks)
        print(f"\n  RESULT: {passed}/{total} checks passed")
        
        print(f"\n  PROMOTION:")
        if self.status == StrategyStatus.CANDIDATE:
            print(f"    ? CANDIDATE FOR PAPER TRADING")
        elif self.status == StrategyStatus.BACKTESTED:
            print(f"    ? NEEDS IMPROVEMENT (review failed checks)")
        else:
            print(f"    ? REJECTED (does not meet minimum criteria)")

class StrategyResearchEngine:
    """Complete strategy research pipeline."""
    
    def __init__(self):
        self.strategies = []
        self.results_dir = Path("research/strategy_engine")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def evaluate_strategy(self, strategy_name: str, metrics: Dict) -> StrategyScorecard:
        """Evaluate a strategy through the complete pipeline."""
        
        # Create scorecard
        scorecard = StrategyScorecard(strategy_name)
        
        # Add metrics
        for name, value in metrics.items():
            scorecard.add_metric(name, value)
        
        # Run validation
        criteria = ValidationCriteria()
        status = scorecard.run_validation(criteria)
        
        # Generate scorecard
        scorecard.generate_scorecard()
        
        # Save results
        self.save_scorecard(scorecard)
        
        return scorecard
    
    def save_scorecard(self, scorecard: StrategyScorecard):
        """Save scorecard to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.results_dir / f"{scorecard.strategy_name}_{timestamp}.json"
        
        data = {
            "strategy": scorecard.strategy_name,
            "status": scorecard.status.value,
            "metrics": scorecard.metrics,
            "checks": scorecard.checks,
            "timestamp": timestamp
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n  Scorecard saved to {filepath}")

# Example usage with our validated strategy
if __name__ == "__main__":
    engine = StrategyResearchEngine()
    
    # Our validated FVG strategy metrics
    fvg_strategy_metrics = {
        "trades": 115,
        "win_rate": 0.47,
        "profit_factor": 1.994,
        "expectancy_r": 0.527,
        "max_drawdown_pct": 11.7,
        "oos_pf": 1.510,
        "walk_forward_pf": 1.423,
        "mc_95_dd": 11.7,
        "calibration_error": 0.037,
        "robustness_score": 1.0,  # 29/29 profitable
        "execution_feasible": True,
        "risk_compliant": True,
        "data_integrity": True
    }
    
    # Evaluate strategy
    scorecard = engine.evaluate_strategy("V4_FVG_H4_LONDON_LONG", fvg_strategy_metrics)
    
    # Example of a strategy that should be rejected
    bad_strategy_metrics = {
        "trades": 50,
        "win_rate": 0.70,
        "profit_factor": 0.95,
        "expectancy_r": -0.05,
        "max_drawdown_pct": 25.0,
        "oos_pf": 0.85,
        "walk_forward_pf": 0.90,
        "mc_95_dd": 35.0,
        "calibration_error": 0.25,
        "robustness_score": 0.2,
        "execution_feasible": False,
        "risk_compliant": False,
        "data_integrity": True
    }
    
    print(f"\n\n{'='*70}")
    print("  EXAMPLE: BAD STRATEGY (Should be rejected)")
    print("="*70)
    bad_scorecard = engine.evaluate_strategy("V2_HIGH_WIN_RATE", bad_strategy_metrics)
