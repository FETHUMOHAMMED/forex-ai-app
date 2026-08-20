"""Automated tests for risk rejection scenarios.
Tests every failure mode we discovered during the audit.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from packages.risk.order_boundary import enforce_order_boundary, RiskGateResult
from packages.risk.hard_position_size import calculate_hard_position_size
from packages.domain.errors import (
    MissingRegimeError, StaleSignalError, RiskViolationError,
    LotSizeError, require_regime, require_not_stale, require_risk_ok,
    require_valid_lot
)

class TestRiskRejection:
    """Tests that dangerous trades are REJECTED"""
    
    def test_1_lot_rejected_on_micro_account(self):
        """1.0 lot on $19 account MUST be rejected"""
        gate = enforce_order_boundary(
            account_balance=19.06, account_equity=19.06, account_free_margin=19.06,
            trades_today=0, max_daily_trades=5, daily_pnl=0, max_daily_loss_pct=0.05,
            open_positions_count=0, max_open_positions=3,
            total_portfolio_risk_pct=0, max_portfolio_risk_pct=0.03,
            symbol="EURUSD", volume=1.0, entry_price=1.15542, stop_loss=1.15718,
            symbol_volume_min=0.01, symbol_volume_max=100, symbol_volume_step=0.01,
            symbol_tick_value=1.0, symbol_tick_size=0.00001,
            symbol_point=0.00001, symbol_contract_size=100000,
            max_risk_pct_per_trade=0.0005,
        )
        assert gate.is_approved == False, "1.0 lot on $19 account should be REJECTED"
        assert gate.result == RiskGateResult.REJECTED_RISK_EXCEEDS_BUDGET
    
    def test_missing_regime_rejects_trade(self):
        """UNKNOWN regime MUST reject trade"""
        with pytest.raises(MissingRegimeError):
            require_regime('UNKNOWN', 'EURUSD')
    
    def test_stale_signal_rejects_trade(self):
        """Stale entry price 1.15123 MUST reject trade"""
        with pytest.raises(StaleSignalError):
            require_not_stale(1.15123, pair='EURUSD')
    
    def test_risk_violation_rejects_trade(self):
        """Actual risk exceeding budget MUST reject"""
        with pytest.raises(RiskViolationError):
            require_risk_ok(176.00, 0.0095, "SL exceeds budget")
    
    def test_invalid_lot_rejects_trade(self):
        """Volume outside broker limits MUST reject"""
        with pytest.raises(LotSizeError):
            require_valid_lot(0.001, 0.01, 100.0)  # Below min
    
    def test_daily_limit_rejects_trade(self):
        """Daily limit reached MUST reject"""
        gate = enforce_order_boundary(
            account_balance=5000, account_equity=5000, account_free_margin=5000,
            trades_today=5, max_daily_trades=5, daily_pnl=0, max_daily_loss_pct=0.05,
            open_positions_count=0, max_open_positions=3,
            total_portfolio_risk_pct=0, max_portfolio_risk_pct=0.03,
            symbol="EURUSD", volume=0.01, entry_price=1.15542, stop_loss=1.15718,
            symbol_volume_min=0.01, symbol_volume_max=100, symbol_volume_step=0.01,
            symbol_tick_value=1.0, symbol_tick_size=0.00001,
            symbol_point=0.00001, symbol_contract_size=100000,
            max_risk_pct_per_trade=0.01,
        )
        assert gate.is_approved == False
        assert gate.result == RiskGateResult.REJECTED_DAILY_LIMIT
    
    def test_valid_trade_passes_all_checks(self):
        """Valid trade on adequately funded account MUST pass"""
        gate = enforce_order_boundary(
            account_balance=5000, account_equity=5000, account_free_margin=5000,
            trades_today=0, max_daily_trades=5, daily_pnl=0, max_daily_loss_pct=0.05,
            open_positions_count=0, max_open_positions=3,
            total_portfolio_risk_pct=0, max_portfolio_risk_pct=0.03,
            symbol="EURUSD", volume=0.01, entry_price=1.15542, stop_loss=1.15718,
            symbol_volume_min=0.01, symbol_volume_max=100, symbol_volume_step=0.01,
            symbol_tick_value=1.0, symbol_tick_size=0.00001,
            symbol_point=0.00001, symbol_contract_size=100000,
            max_risk_pct_per_trade=0.01,
        )
        assert gate.is_approved == True
        assert gate.result == RiskGateResult.APPROVED

class TestHardPositionSizing:
    """Tests for hard position sizing calculations"""
    
    def test_micro_account_rejected(self):
        """$19 account with 0.05% risk should be rejected (broker min too large)"""
        result = calculate_hard_position_size(
            equity=19.06, risk_percent=0.0005,
            contract_size=100000, tick_value=1.0, tick_size=0.00001, point=0.00001,
            volume_min=0.01, volume_max=200, volume_step=0.01,
            entry_price=1.15542, stop_loss=1.15718,
        )
        assert result.is_safe == False, "Hard invariant must fail for $19 account"
        assert result.actual_sl_risk > result.risk_money
    
    def test_adequate_account_approved(self):
        """$3520+ account with 0.05% risk should be approved"""
        result = calculate_hard_position_size(
            equity=3520, risk_percent=0.0005,
            contract_size=100000, tick_value=1.0, tick_size=0.00001, point=0.00001,
            volume_min=0.01, volume_max=200, volume_step=0.01,
            entry_price=1.15542, stop_loss=1.15718,
        )
        assert result.is_safe == True, f"Hard invariant should pass for ${3520} account"
        assert result.final_volume >= 0.01

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
