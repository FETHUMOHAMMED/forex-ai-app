"""CAPITAL DEPLOYMENT DECISION - Separate from risk gate."""
import json
from pathlib import Path
from datetime import datetime

class CapitalDeploymentFramework:
    """Separates 'can we trade?' from 'should we fund?'"""
    
    def __init__(self):
        self.decision = None
        
    def evaluate_capital_deployment(self):
        """Evaluate whether strategy should receive capital."""
        
        decision = {
            "timestamp": datetime.now().isoformat(),
            
            "two_separate_questions": {
                "risk_gate_question": "Can this trade be safely executed?",
                "strategy_question": "Should this strategy receive capital?",
                "answer_risk_gate": "YES - $3,520 supports 0.25% risk",
                "answer_strategy": "NOT YET - insufficient live validation"
            },
            
            "current_evidence": {
                "backtest": {
                    "usdjpy_pf": 1.852,
                    "usdjpy_p_value": 0.0049,
                    "status": "STRONG in backtest"
                },
                "full_sample": {
                    "pf": 1.140,
                    "p_value": 0.226,
                    "status": "WEAK aggregate"
                },
                "walk_forward": {
                    "pf": 1.248,
                    "expectancy": 0.151,
                    "p_value": 0.132,
                    "status": "MARGINAL"
                },
                "monte_carlo": {
                    "worst_dd": 43.3,
                    "worst_streak": 26,
                    "recovery_months": 52,
                    "status": "HIGH RISK"
                },
                "live_validation": {
                    "qualified_trades": 0,
                    "paper_trades": 0,
                    "status": "INSUFFICIENT"
                }
            },
            
            "capital_deployment_decision": {
                "should_fund_now": False,
                "reason": "Strategy validation incomplete",
                "required_before_funding": [
                    "90+ days paper trading",
                    "20+ paper trades documented",
                    "Paper trading matches walk-forward (PF > 1.2)",
                    "Paper trading shows positive expectancy",
                    "Psychological readiness confirmed"
                ]
            },
            
            "recommended_path": {
                "phase_1": {
                    "duration": "90 days",
                    "action": "Paper trade extensively",
                    "capital": "$0 (no real money)",
                    "goal": "20+ paper trades"
                },
                "phase_2": {
                    "duration": "After paper validation",
                    "action": "Controlled live with MINIMUM capital",
                    "capital": "$2,000 (NOT $3,520)",
                    "goal": "Validate execution, not make money"
                },
                "phase_3": {
                    "duration": "After 3 months live",
                    "action": "If edge confirmed, consider scaling",
                    "capital": "$3,520+ only if justified",
                    "goal": "Gradual capital deployment"
                }
            },
            
            "risk_management": {
                "initial_risk": "0.25% per trade",
                "max_risk": "0.25% until 100+ live trades",
                "position_sizing": "Based on 43R worst case",
                "daily_loss_limit": "-1%",
                "weekly_loss_limit": "-2%",
                "monthly_loss_limit": "-4%"
            },
            
            "what_not_to_do": [
                "Do NOT deposit $3,520 yet",
                "Do NOT skip paper trading",
                "Do NOT risk more than 0.25%",
                "Do NOT expect backtest-level returns",
                "Do NOT trade without 20+ paper trades"
            ]
        }
        
        self.decision = decision
        return decision
    
    def display_decision(self):
        """Display capital deployment decision."""
        if not self.decision:
            self.evaluate_capital_deployment()
        
        d = self.decision
        
        print("="*70)
        print("  CAPITAL DEPLOYMENT DECISION")
        print("="*70)
        
        print(f"\n  THE TWO SEPARATE QUESTIONS:")
        print(f"  1. {d['two_separate_questions']['risk_gate_question']}")
        print(f"     Answer: {d['two_separate_questions']['answer_risk_gate']}")
        print(f"  2. {d['two_separate_questions']['strategy_question']}")
        print(f"     Answer: {d['two_separate_questions']['answer_strategy']}")
        
        print(f"\n{'='*70}")
        print("  CURRENT EVIDENCE")
        print("="*70)
        
        evidence = d['current_evidence']
        print(f"\n  Backtest: {evidence['backtest']['status']}")
        print(f"  Full Sample: {evidence['full_sample']['status']}")
        print(f"  Walk-Forward: {evidence['walk_forward']['status']}")
        print(f"  Monte Carlo: {evidence['monte_carlo']['status']}")
        print(f"  Live Validation: {evidence['live_validation']['status']}")
        
        print(f"\n{'='*70}")
        print("  CAPITAL DECISION")
        print("="*70)
        
        decision = d['capital_deployment_decision']
        print(f"\n  Should fund now: {'YES' if decision['should_fund_now'] else 'NO'}")
        print(f"  Reason: {decision['reason']}")
        
        print(f"\n  Required before funding:")
        for req in decision['required_before_funding']:
            print(f"    ? {req}")
        
        print(f"\n{'='*70}")
        print("  RECOMMENDED PATH")
        print("="*70)
        
        for phase, details in d['recommended_path'].items():
            print(f"\n  {phase.replace('_', ' ').upper()}:")
            print(f"    Duration: {details['duration']}")
            print(f"    Action: {details['action']}")
            print(f"    Capital: {details['capital']}")
            print(f"    Goal: {details['goal']}")
        
        print(f"\n{'='*70}")
        print("  RISK MANAGEMENT")
        print("="*70)
        
        risk = d['risk_management']
        for key, value in risk.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        
        print(f"\n{'='*70}")
        print("  WHAT NOT TO DO")
        print("="*70)
        
        for warning in d['what_not_to_do']:
            print(f"  ? {warning}")
    
    def save_decision(self):
        """Save decision for reference."""
        if not self.decision:
            self.evaluate_capital_deployment()
        
        filepath = Path("research/capital_deployment_decision.json")
        with open(filepath, 'w') as f:
            json.dump(self.decision, f, indent=2)
        
        print(f"\n\nDecision saved to {filepath}")

if __name__ == "__main__":
    framework = CapitalDeploymentFramework()
    framework.evaluate_capital_deployment()
    framework.display_decision()
    framework.save_decision()
