"""Control Plane - THE authoritative trading decision.
Consumes System Integrity Gate results -> produces TRADING_ALLOWED.
Independent: does NOT depend on the systems it monitors.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum

class TradingState(str, Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    PENDING_RECOVERY = "PENDING_RECOVERY"

class ControlPlane:
    """
    THE single decision point for trading.
    Reads scanner results -> produces TRADING_ALLOWED.
    """
    
    def __init__(self):
        self.state = TradingState.BLOCKED  # Fail closed by default
        self.last_decision = None
        self.decision_history = []
    
    def evaluate(self, scanner_result: dict) -> TradingState:
        """
        Evaluate scanner result and determine trading state.
        FAIL CLOSED: any critical failure = BLOCKED.
        """
        overall = scanner_result.get("overall", "HALT")
        trading_allowed = scanner_result.get("trading_allowed", False)
        
        if overall == "READY" and trading_allowed:
            self.state = TradingState.ALLOWED
        elif overall == "DEGRADED":
            # Non-critical failures - check if any critical exists
            criticals = scanner_result.get("critical_errors", [])
            if criticals:
                self.state = TradingState.BLOCKED
            else:
                self.state = TradingState.ALLOWED
        else:
            # HALT or missing data = BLOCKED (fail closed)
            self.state = TradingState.BLOCKED
        
        self.last_decision = {
            "state": self.state.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scanner_result": scanner_result,
        }
        self.decision_history.append(self.last_decision)
        
        return self.state
    
    def can_trade(self) -> bool:
        """THE method every execution path must call before order_send"""
        return self.state == TradingState.ALLOWED
    
    def assert_can_trade(self):
        """Raises if trading not allowed"""
        if not self.can_trade():
            raise TradingBlockedError(f"Trading blocked: system state = {self.state.value}")


class TradingBlockedError(Exception):
    pass


# Global instance - THE control plane
control_plane = ControlPlane()


if __name__ == "__main__":
    print("=" * 65)
    print("  CONTROL PLANE - Trading Decision")
    print("=" * 65)
    
    # Test with scanner result
    scanner_result = {
        "overall": "HALT",
        "trading_allowed": False,
        "critical_errors": [
            {"code": "RISK_WITHIN_BUDGET", "severity": "CRITICAL"}
        ],
    }
    
    state = control_plane.evaluate(scanner_result)
    print(f"\n  Scanner: HALT (risk budget exceeded)")
    print(f"  Control Plane: {state.value}")
    print(f"  TRADING ALLOWED: {control_plane.can_trade()}")
    
    # Test assert
    print(f"\n  Order attempt:")
    try:
        control_plane.assert_can_trade()
        print(f"  Order ALLOWED")
    except TradingBlockedError as e:
        print(f"  {e}")
    
    print(f"\n{'='*65}")
