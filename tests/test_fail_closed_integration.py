"""Integration test: break systems and verify fail-closed behavior."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from packages.integrity.control_plane import ControlPlane, TradingState, TradingBlockedError

class TestFailClosed:
    """Every failure must result in BLOCKED trading."""
    
    def test_halt_blocks_trading(self):
        cp = ControlPlane()
        result = {"overall": "HALT", "trading_allowed": False, "critical_errors": []}
        state = cp.evaluate(result)
        assert state == TradingState.BLOCKED
        assert not cp.can_trade()
    
    def test_ready_allows_trading(self):
        cp = ControlPlane()
        result = {"overall": "READY", "trading_allowed": True, "critical_errors": []}
        state = cp.evaluate(result)
        assert state == TradingState.ALLOWED
        assert cp.can_trade()
    
    def test_risk_failure_blocks(self):
        cp = ControlPlane()
        result = {
            "overall": "HALT", "trading_allowed": False,
            "critical_errors": [{"code": "RISK_WITHIN_BUDGET", "severity": "CRITICAL"}]
        }
        state = cp.evaluate(result)
        assert state == TradingState.BLOCKED
        with pytest.raises(TradingBlockedError):
            cp.assert_can_trade()
    
    def test_mt5_failure_blocks(self):
        cp = ControlPlane()
        result = {
            "overall": "HALT", "trading_allowed": False,
            "critical_errors": [{"code": "MT5_DISCONNECTED", "severity": "CRITICAL"}]
        }
        state = cp.evaluate(result)
        assert state == TradingState.BLOCKED
    
    def test_degraded_without_critical_allows(self):
        cp = ControlPlane()
        result = {
            "overall": "DEGRADED", "trading_allowed": True,
            "critical_errors": []
        }
        state = cp.evaluate(result)
        assert state == TradingState.ALLOWED
    
    def test_missing_data_fails_closed(self):
        cp = ControlPlane()
        # Missing scanner result = fail closed
        result = {}
        state = cp.evaluate(result)
        assert state == TradingState.BLOCKED
        assert not cp.can_trade()
    
    def test_default_state_is_blocked(self):
        cp = ControlPlane()
        # Before any evaluation, must be BLOCKED (fail closed)
        assert cp.state == TradingState.BLOCKED
        assert not cp.can_trade()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
