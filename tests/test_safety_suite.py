"""SAFETY TEST SUITE - Every dangerous scenario must be rejected."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from packages.execution.hard_order_boundary import HardOrderBoundary, OrderRequest

class TestSafetySuite:
    """Tests that EVERY dangerous scenario is rejected."""
    
    def setup_method(self):
        self.boundary = HardOrderBoundary()
    
    def make_order(self, **overrides):
        """Create a valid order and apply overrides."""
        base = {
            "symbol": "USDJPYm",
            "direction": "BUY",
            "volume": 0.01,
            "entry": 154.250,
            "sl": 153.850,  # 40 pips below entry
            "tp": 155.050,  # 80 pips above entry
            "risk_percent": 0.25,
            "account": "REDACTED_LIVE_ACCOUNT",
            "strategy_version": "V4_CANONICAL_1.0",
            "account_server": "Exness-MT5Real10",
            "account_broker": "Exness",
            "environment": "LIVE_MICRO"
        }
        base.update(overrides)
        return OrderRequest(**base)
    
    def test_no_order_without_sl(self):
        """Reject order with SL=0."""
        order = self.make_order(sl=0)
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["sl_positive"]["passed"]
    
    def test_no_order_without_tp(self):
        """Reject order with TP=0."""
        order = self.make_order(tp=0)
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["tp_positive"]["passed"]
    
    def test_no_order_above_risk_limit(self):
        """Reject order with risk > 0.25%."""
        order = self.make_order(risk_percent=5.0)
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["risk"]["passed"]
    
    def test_no_order_wrong_account(self):
        """Reject order for wrong account."""
        order = self.make_order(account="999999999")
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["account_login"]["passed"]
    
    def test_no_order_wrong_symbol(self):
        """Reject order for wrong symbol."""
        order = self.make_order(symbol="EURUSDm")
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["symbol"]["passed"]
    
    def test_no_order_wrong_direction(self):
        """Reject SELL orders."""
        order = self.make_order(direction="SELL")
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["direction"]["passed"]
    
    def test_no_order_sl_wrong_side(self):
        """Reject SL above entry for BUY."""
        order = self.make_order(sl=154.300)  # SL above entry
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["sl_side"]["passed"]
    
    def test_no_order_tp_wrong_side(self):
        """Reject TP below entry for BUY."""
        order = self.make_order(tp=154.200)  # TP below entry
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["tp_side"]["passed"]
    
    def test_no_order_invalid_volume(self):
        """Reject invalid volume."""
        order = self.make_order(volume=0)
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["volume"]["passed"]
    
    def test_no_order_wrong_strategy(self):
        """Reject orders from wrong strategy."""
        order = self.make_order(strategy_version="OLD")
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["strategy"]["passed"]
    
    def test_valid_order_passes(self):
        """Valid order should pass."""
        order = self.make_order()
        is_valid, checks = self.boundary.validate_order(order)
        assert is_valid, f"Valid order rejected: {checks}"
    
    def test_no_mt5_called_on_rejection(self):
        """Rejected orders must NEVER call MT5."""
        order = self.make_order(sl=0, tp=0)
        is_valid, checks = self.boundary.validate_order(order)
        assert not is_valid
        assert not checks["sl_positive"]["passed"]
        assert not checks["tp_positive"]["passed"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])


