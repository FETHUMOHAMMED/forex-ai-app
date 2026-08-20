"""LAYERED ARCHITECTURE - AI can influence, never override."""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List
from datetime import datetime, timezone
import json

class PlaneStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"

class DecisionAuthority(Enum):
    AI_CAN_INFLUENCE = "AI_CAN_INFLUENCE"
    AI_CANNOT_OVERRIDE = "AI_CANNOT_OVERRIDE"
    NO_AI_INVOLVEMENT = "NO_AI_INVOLVEMENT"

@dataclass
class PlaneResult:
    plane: str
    status: PlaneStatus
    authority: DecisionAuthority
    reason: str
    details: Dict = None

class LayeredExecutionSystem:
    """Enforces strict plane separation with AI boundaries."""
    
    def __init__(self):
        self.planes = []
        self.ai_allowed_planes = ["STRATEGY"]
        self.ai_influence_planes = ["STRATEGY"]
        self.no_ai_planes = [
            "CONTROL", "RISK", "EXECUTION", "MT5_IDENTITY",
            "SPREAD", "SL_VALIDITY", "TP_VALIDITY", "FRESHNESS",
            "POSITION_LIMITS", "DAILY_LOSS", "CIRCUIT_BREAKER"
        ]
    
    def strategy_plane(self, setup: Dict, ai_confidence: float) -> PlaneResult:
        """
        STRATEGY PLANE - AI CAN influence here.
        Determines if a valid setup exists.
        """
        # Baseline strategy checks (deterministic)
        has_fvg = setup.get("has_fvg", False)
        is_london_session = setup.get("is_london_session", False)
        is_bullish_bias = setup.get("is_bullish_bias", False)
        
        baseline_valid = all([has_fvg, is_london_session, is_bullish_bias])
        
        # AI can influence by adjusting confidence threshold
        # But AI cannot create a setup where none exists
        if not baseline_valid:
            return PlaneResult(
                plane="STRATEGY",
                status=PlaneStatus.FAIL,
                authority=DecisionAuthority.AI_CANNOT_OVERRIDE,
                reason="Baseline setup criteria not met",
                details={"ai_confidence": ai_confidence}
            )
        
        # AI can influence the decision within valid setups
        # AI says: high confidence ? proceed
        # AI says: low confidence ? skip (but doesn't override safety)
        ai_adjusted_threshold = 0.5 if ai_confidence > 0.6 else 0.7
        setup_quality = setup.get("setup_quality", 0.5)
        
        if setup_quality < ai_adjusted_threshold:
            return PlaneResult(
                plane="STRATEGY",
                status=PlaneStatus.SKIP,
                authority=DecisionAuthority.AI_CAN_INFLUENCE,
                reason=f"AI filtered setup (confidence: {ai_confidence:.2f})",
                details={"ai_confidence": ai_confidence}
            )
        
        return PlaneResult(
            plane="STRATEGY",
            status=PlaneStatus.PASS,
            authority=DecisionAuthority.AI_CAN_INFLUENCE,
            reason="Valid setup with AI confirmation",
            details={"ai_confidence": ai_confidence}
        )
    
    def control_plane(self, system_state: Dict) -> PlaneResult:
        """
        CONTROL PLANE - NO AI involvement.
        Checks system integrity and safety.
        """
        checks = {
            "system_healthy": system_state.get("system_healthy", False),
            "no_alerts": system_state.get("no_alerts", False),
            "data_fresh": system_state.get("data_fresh", False),
        }
        
        all_pass = all(checks.values())
        
        return PlaneResult(
            plane="CONTROL",
            status=PlaneStatus.PASS if all_pass else PlaneStatus.FAIL,
            authority=DecisionAuthority.NO_AI_INVOLVEMENT,
            reason="Control checks passed" if all_pass else f"Control failure: {checks}",
            details=checks
        )
    
    def risk_plane(self, risk_state: Dict) -> PlaneResult:
        """
        RISK PLANE - NO AI involvement.
        Checks if we can afford the trade.
        """
        checks = {
            "risk_budget_ok": risk_state.get("risk_budget_ok", False),
            "position_size_valid": risk_state.get("position_size_valid", False),
            "max_daily_loss_ok": risk_state.get("max_daily_loss_ok", False),
            "drawdown_ok": risk_state.get("drawdown_ok", False),
        }
        
        all_pass = all(checks.values())
        
        return PlaneResult(
            plane="RISK",
            status=PlaneStatus.PASS if all_pass else PlaneStatus.FAIL,
            authority=DecisionAuthority.NO_AI_INVOLVEMENT,
            reason="Risk checks passed" if all_pass else f"Risk failure: {checks}",
            details=checks
        )
    
    def execution_plane(self, execution_state: Dict) -> PlaneResult:
        """
        EXECUTION PLANE - NO AI involvement.
        Checks execution safety.
        """
        checks = {
            "mt5_connected": execution_state.get("mt5_connected", False),
            "account_matches": execution_state.get("account_matches", False),
            "symbol_valid": execution_state.get("symbol_valid", False),
            "spread_acceptable": execution_state.get("spread_acceptable", False),
            "sl_valid": execution_state.get("sl_valid", False),
            "tp_valid": execution_state.get("tp_valid", False),
            "signal_fresh": execution_state.get("signal_fresh", False),
            "position_limit_ok": execution_state.get("position_limit_ok", False),
            "circuit_breaker_ok": execution_state.get("circuit_breaker_ok", False),
        }
        
        all_pass = all(checks.values())
        
        return PlaneResult(
            plane="EXECUTION",
            status=PlaneStatus.PASS if all_pass else PlaneStatus.FAIL,
            authority=DecisionAuthority.NO_AI_INVOLVEMENT,
            reason="Execution checks passed" if all_pass else f"Execution failure: {checks}",
            details=checks
        )
    
    def process_signal(self, 
                      setup: Dict,
                      ai_confidence: float,
                      system_state: Dict,
                      risk_state: Dict,
                      execution_state: Dict) -> List[PlaneResult]:
        """Process a signal through all planes in order."""
        
        results = []
        
        # 1. STRATEGY PLANE (AI can influence)
        strategy_result = self.strategy_plane(setup, ai_confidence)
        results.append(strategy_result)
        
        if strategy_result.status == PlaneStatus.FAIL:
            return results  # Stop if no valid setup
        
        if strategy_result.status == PlaneStatus.SKIP:
            return results  # Stop if AI filters setup
        
        # 2. CONTROL PLANE (No AI)
        control_result = self.control_plane(system_state)
        results.append(control_result)
        
        if control_result.status == PlaneStatus.FAIL:
            return results  # Stop if control fails
        
        # 3. RISK PLANE (No AI)
        risk_result = self.risk_plane(risk_state)
        results.append(risk_result)
        
        if risk_result.status == PlaneStatus.FAIL:
            return results  # Stop if risk fails
        
        # 4. EXECUTION PLANE (No AI)
        execution_result = self.execution_plane(execution_state)
        results.append(execution_result)
        
        return results
    
    def should_execute(self, results: List[PlaneResult]) -> bool:
        """Check if all planes passed."""
        if not results:
            return False
        
        return all(r.status == PlaneStatus.PASS for r in results)

class MT5ExecutionInterface:
    """Final execution layer - only called if all planes pass."""
    
    def __init__(self):
        self.execution_count = 0
        self.last_execution = None
    
    def execute(self, trade_details: Dict):
        """Execute trade only if called."""
        # This should ONLY be called if all planes pass
        self.execution_count += 1
        self.last_execution = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trade": trade_details
        }
        
        # In forward test, just record
        return {
            "status": "EXECUTED",
            "execution_count": self.execution_count,
            "trade": trade_details
        }
    
    def verify_no_execution(self):
        """Verify MT5 was never called."""
        return self.execution_count == 0

if __name__ == "__main__":
    # Test the layered architecture
    system = LayeredExecutionSystem()
    mt5_interface = MT5ExecutionInterface()
    
    # Test Case 1: AI says BUY but risk fails
    print("="*70)
    print("  TEST CASE 1: AI BUY but RISK FAILS")
    print("="*70)
    
    setup = {
        "has_fvg": True,
        "is_london_session": True,
        "is_bullish_bias": True,
        "setup_quality": 0.8
    }
    
    ai_confidence = 0.91  # AI very confident
    
    system_state = {
        "system_healthy": True,
        "no_alerts": True,
        "data_fresh": True,
    }
    
    risk_state = {
        "risk_budget_ok": False,  # RISK FAILS
        "position_size_valid": False,
        "max_daily_loss_ok": False,
        "drawdown_ok": True,
    }
    
    execution_state = {
        "mt5_connected": True,
        "account_matches": True,
        "symbol_valid": True,
        "spread_acceptable": True,
        "sl_valid": True,
        "tp_valid": True,
        "signal_fresh": True,
        "position_limit_ok": True,
        "circuit_breaker_ok": True,
    }
    
    results = system.process_signal(setup, ai_confidence, system_state, risk_state, execution_state)
    
    print(f"\nAI Confidence: {ai_confidence}")
    print(f"AI says: BUY")
    print(f"\nPlane results:")
    for result in results:
        print(f"  {result.plane}: {result.status.value} ({result.authority.value})")
        print(f"    Reason: {result.reason}")
    
    should_execute = system.should_execute(results)
    print(f"\nFinal decision: {'EXECUTE' if should_execute else 'BLOCK'}")
    print(f"MT5 calls: {mt5_interface.execution_count}")
    print(f"Result: AI could NOT override risk plane ?")
    
    # Test Case 2: AI says BUY and everything passes
    print(f"\n{'='*70}")
    print("  TEST CASE 2: AI BUY and ALL PASS")
    print("="*70)
    
    risk_state_ok = {
        "risk_budget_ok": True,
        "position_size_valid": True,
        "max_daily_loss_ok": True,
        "drawdown_ok": True,
    }
    
    results = system.process_signal(setup, ai_confidence, system_state, risk_state_ok, execution_state)
    
    print(f"\nAI Confidence: {ai_confidence}")
    print(f"AI says: BUY")
    print(f"\nPlane results:")
    for result in results:
        print(f"  {result.plane}: {result.status.value} ({result.authority.value})")
        print(f"    Reason: {result.reason}")
    
    should_execute = system.should_execute(results)
    print(f"\nFinal decision: {'EXECUTE' if should_execute else 'BLOCK'}")
    
    if should_execute:
        trade = {
            "direction": "BUY",
            "entry": 154.250,
            "sl": 153.850,
            "tp": 155.250
        }
        execution_result = mt5_interface.execute(trade)
        print(f"Execution: {execution_result['status']}")
        print(f"MT5 calls: {mt5_interface.execution_count}")
