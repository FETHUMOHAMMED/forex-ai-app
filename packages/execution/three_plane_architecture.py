"""THREE-PLANE ARCHITECTURE - Permanent separation."""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timezone
import json
from pathlib import Path

class PlaneType(Enum):
    STRATEGY = "STRATEGY"
    CONTROL = "CONTROL"
    CAPITAL = "CAPITAL"

class PlaneStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"
    NOT_APPLICABLE = "NOT_APPLICABLE"

@dataclass
class PlaneDecision:
    plane: PlaneType
    question: str
    answer: str
    status: PlaneStatus
    details: Dict
    timestamp: str

class ThreePlaneSystem:
    """Permanent three-plane separation for institutional trading."""
    
    def __init__(self):
        self.planes = {
            PlaneType.STRATEGY: self.strategy_plane,
            PlaneType.CONTROL: self.control_plane,
            PlaneType.CAPITAL: self.capital_plane,
        }
        self.decisions_log = []
        
    def strategy_plane(self, market_data: Dict, strategy_state: Dict) -> PlaneDecision:
        """
        STRATEGY PLANE
        Question: Should we trade?
        Determines if there's a valid edge.
        """
        question = "Should we trade?"
        
        # Strategy conditions
        has_fvg = market_data.get("has_fvg", False)
        is_bullish = market_data.get("is_bullish", False)
        is_good_session = market_data.get("is_good_session", False)
        expected_edge = strategy_state.get("expected_edge", 0)
        
        conditions_met = all([has_fvg, is_bullish, is_good_session])
        edge_positive = expected_edge > 0.1
        
        if conditions_met and edge_positive:
            return PlaneDecision(
                plane=PlaneType.STRATEGY,
                question=question,
                answer="YES - Trade setup valid",
                status=PlaneStatus.PASS,
                details={
                    "setup": "FVG_BULLISH",
                    "expected_edge_r": expected_edge,
                    "confidence": strategy_state.get("confidence", 0)
                },
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        else:
            return PlaneDecision(
                plane=PlaneType.STRATEGY,
                question=question,
                answer="NO - No valid setup",
                status=PlaneStatus.FAIL,
                details={
                    "has_fvg": has_fvg,
                    "is_bullish": is_bullish,
                    "is_good_session": is_good_session,
                    "expected_edge_r": expected_edge
                },
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    def control_plane(self, execution_state: Dict) -> PlaneDecision:
        """
        CONTROL PLANE
        Question: Is it safe to trade?
        Checks all safety conditions.
        """
        question = "Is it safe to trade?"
        
        # Required safety checks
        checks = {
            "signal_fresh": execution_state.get("signal_fresh", False),
            "entry_deviation_ok": execution_state.get("entry_deviation_ok", False),
            "spread_acceptable": execution_state.get("spread_acceptable", False),
            "sl_valid": execution_state.get("sl_valid", False),
            "tp_valid": execution_state.get("tp_valid", False),
            "risk_budget_ok": execution_state.get("risk_budget_ok", False),
            "account_matches": execution_state.get("account_matches", False),
            "symbol_valid": execution_state.get("symbol_valid", False),
            "no_duplicate": execution_state.get("no_duplicate", False),
            "session_valid": execution_state.get("session_valid", False),
            "margin_available": execution_state.get("margin_available", False),
            "mt5_connected": execution_state.get("mt5_connected", False),
        }
        
        failed_checks = {k: v for k, v in checks.items() if not v}
        all_pass = len(failed_checks) == 0
        
        return PlaneDecision(
            plane=PlaneType.CONTROL,
            question=question,
            answer="YES - All safety checks passed" if all_pass else f"NO - {len(failed_checks)} checks failed",
            status=PlaneStatus.PASS if all_pass else PlaneStatus.FAIL,
            details={
                "total_checks": len(checks),
                "passed_checks": len(checks) - len(failed_checks),
                "failed_checks": failed_checks
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def capital_plane(self, strategy_performance: Dict, capital_state: Dict) -> PlaneDecision:
        """
        CAPITAL PLANE
        Question: How much capital should this strategy receive?
        Determines capital allocation based on validation.
        """
        question = "How much capital should this strategy receive?"
        
        # Strategy validation metrics
        walk_forward_pf = strategy_performance.get("walk_forward_pf", 0)
        walk_forward_expectancy = strategy_performance.get("walk_forward_expectancy", 0)
        monte_carlo_worst_dd = strategy_performance.get("monte_carlo_worst_dd", 100)
        live_trades = strategy_performance.get("live_trades", 0)
        paper_trades = strategy_performance.get("paper_trades", 0)
        
        # Capital allocation logic
        if live_trades >= 100 and walk_forward_pf > 1.3:
            allocation_pct = 1.0  # Full allocation after proven live
            status = PlaneStatus.PASS
            answer = f"FULL allocation ({allocation_pct*100}%)"
        elif paper_trades >= 20 and walk_forward_pf > 1.2:
            allocation_pct = 0.5  # Half allocation after paper validation
            status = PlaneStatus.PASS
            answer = f"HALF allocation ({allocation_pct*100}%)"
        elif paper_trades >= 10:
            allocation_pct = 0.25  # Quarter allocation for initial testing
            status = PlaneStatus.PENDING
            answer = f"MINIMAL allocation ({allocation_pct*100}%)"
        else:
            allocation_pct = 0.0  # No allocation without validation
            status = PlaneStatus.FAIL
            answer = "NO allocation - insufficient validation"
        
        # Calculate suggested capital
        available_capital = capital_state.get("available_capital", 0)
        suggested_capital = available_capital * allocation_pct
        
        return PlaneDecision(
            plane=PlaneType.CAPITAL,
            question=question,
            answer=answer,
            status=status,
            details={
                "allocation_pct": allocation_pct,
                "suggested_capital": suggested_capital,
                "walk_forward_pf": walk_forward_pf,
                "walk_forward_expectancy": walk_forward_expectancy,
                "monte_carlo_worst_dd": monte_carlo_worst_dd,
                "live_trades": live_trades,
                "paper_trades": paper_trades,
                "allocation_rationale": self.get_allocation_rationale(
                    live_trades, paper_trades, walk_forward_pf
                )
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def get_allocation_rationale(self, live_trades: int, paper_trades: int, wf_pf: float) -> str:
        """Explain capital allocation rationale."""
        if live_trades >= 100:
            return "Proven live performance"
        elif paper_trades >= 20 and wf_pf > 1.2:
            return "Paper validation complete, walk-forward positive"
        elif paper_trades >= 10:
            return "Initial paper trading, limited validation"
        else:
            return "Insufficient validation to risk capital"
    
    def process_full_pipeline(self, 
                             market_data: Dict,
                             strategy_state: Dict,
                             execution_state: Dict,
                             strategy_performance: Dict,
                             capital_state: Dict) -> List[PlaneDecision]:
        """Process through all three planes."""
        
        decisions = []
        
        # 1. STRATEGY PLANE
        strategy_decision = self.strategy_plane(market_data, strategy_state)
        decisions.append(strategy_decision)
        
        # If strategy says no, stop
        if strategy_decision.status != PlaneStatus.PASS:
            return decisions
        
        # 2. CONTROL PLANE
        control_decision = self.control_plane(execution_state)
        decisions.append(control_decision)
        
        # If control says no, stop
        if control_decision.status != PlaneStatus.PASS:
            return decisions
        
        # 3. CAPITAL PLANE
        capital_decision = self.capital_plane(strategy_performance, capital_state)
        decisions.append(capital_decision)
        
        return decisions
    
    def display_pipeline(self, decisions: List[PlaneDecision]):
        """Display pipeline decisions."""
        print("="*70)
        print("  THREE-PLANE DECISION PIPELINE")
        print("="*70)
        
        for decision in decisions:
            print(f"\n  {decision.plane.value} PLANE:")
            print(f"    Question: {decision.question}")
            print(f"    Answer: {decision.answer}")
            print(f"    Status: {decision.status.value}")
            
            if decision.details:
                print(f"    Details:")
                for key, value in decision.details.items():
                    if isinstance(value, dict):
                        print(f"      {key}:")
                        for k, v in value.items():
                            print(f"        {k}: {v}")
                    else:
                        print(f"      {key}: {value}")
        
        # Final verdict
        all_pass = all(d.status == PlaneStatus.PASS for d in decisions)
        print(f"\n{'='*70}")
        print("  FINAL VERDICT")
        print("="*70)
        
        if all_pass:
            print("  ? ALL PLANES PASSED - CAN EXECUTE")
        else:
            print("  ? BLOCKED - One or more planes failed")
            for d in decisions:
                if d.status != PlaneStatus.PASS:
                    print(f"    Blocked by: {d.plane.value} plane")
    
    def save_pipeline_log(self, decisions: List[PlaneDecision]):
        """Save pipeline decisions."""
        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decisions": [
                {
                    "plane": d.plane.value,
                    "question": d.question,
                    "answer": d.answer,
                    "status": d.status.value,
                    "details": d.details
                }
                for d in decisions
            ]
        }
        
        log_dir = Path("research/pipeline_logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, 'w') as f:
            json.dump(log, f, indent=2, default=str)
        
        return filepath

if __name__ == "__main__":
    system = ThreePlaneSystem()
    
    # Test Case 1: All planes pass
    print("TEST CASE 1: All planes pass")
    print("="*70)
    
    market_data = {
        "has_fvg": True,
        "is_bullish": True,
        "is_good_session": True,
    }
    
    strategy_state = {
        "expected_edge": 0.159,
        "confidence": 0.55,
    }
    
    execution_state = {
        "signal_fresh": True,
        "entry_deviation_ok": True,
        "spread_acceptable": True,
        "sl_valid": True,
        "tp_valid": True,
        "risk_budget_ok": True,
        "account_matches": True,
        "symbol_valid": True,
        "no_duplicate": True,
        "session_valid": True,
        "margin_available": True,
        "mt5_connected": True,
    }
    
    strategy_performance = {
        "walk_forward_pf": 1.248,
        "walk_forward_expectancy": 0.151,
        "monte_carlo_worst_dd": 43.3,
        "live_trades": 0,
        "paper_trades": 25,
    }
    
    capital_state = {
        "available_capital": 2000,
    }
    
    decisions = system.process_full_pipeline(
        market_data, strategy_state, execution_state,
        strategy_performance, capital_state
    )
    system.display_pipeline(decisions)
    
    # Test Case 2: Capital plane blocks
    print(f"\n\nTEST CASE 2: Capital plane blocks (insufficient validation)")
    print("="*70)
    
    strategy_performance_no_validation = {
        "walk_forward_pf": 1.248,
        "walk_forward_expectancy": 0.151,
        "monte_carlo_worst_dd": 43.3,
        "live_trades": 0,
        "paper_trades": 5,  # Insufficient paper trades
    }
    
    decisions = system.process_full_pipeline(
        market_data, strategy_state, execution_state,
        strategy_performance_no_validation, capital_state
    )
    system.display_pipeline(decisions)
