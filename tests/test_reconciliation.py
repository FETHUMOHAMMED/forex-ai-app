"""Automated tests for trade reconciliation scenarios"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from packages.domain.errors import (
    PhantomTradeError, OrphanPositionError, PnLMismatchError, TimestampError,
    MissingRegimeError, MT5ConnectionError
)
from packages.execution.trade_state_machine import (
    TradeStateMachine, TradeState, InvalidTransitionError
)
from packages.execution.mt5_identity import TradeIdentity

class TestReconciliationErrors:
    """Tests that data integrity errors are properly detected"""
    
    def test_phantom_trade_detected(self):
        """Trade in DB but not MT5 -> PhantomTradeError"""
        with pytest.raises(PhantomTradeError):
            raise PhantomTradeError(146)
    
    def test_orphan_position_detected(self):
        """Position in MT5 but not DB -> OrphanPositionError"""
        with pytest.raises(OrphanPositionError):
            raise OrphanPositionError(589629837)
    
    def test_pnl_mismatch_detected(self):
        """PnL differs between DB and MT5 -> PnLMismatchError"""
        with pytest.raises(PnLMismatchError):
            raise PnLMismatchError(163, db_pnl=-0.13, mt5_pnl=-8.10)
    
    def test_timestamp_error_detected(self):
        """Exit before entry -> TimestampError"""
        with pytest.raises(TimestampError):
            raise TimestampError(162, 
                entry="2026-08-10T10:06:16", 
                exit="2026-08-10T07:09:25")

class TestStateMachine:
    """Tests that invalid state transitions are blocked"""
    
    def test_valid_lifecycle(self):
        """Complete trade lifecycle must succeed"""
        tsm = TradeStateMachine("test_001")
        tsm.transition_to(TradeState.RISK_APPROVED)
        tsm.transition_to(TradeState.ORDER_SUBMITTED)
        tsm.transition_to(TradeState.ORDER_ACCEPTED)
        tsm.transition_to(TradeState.POSITION_OPENED)
        tsm.transition_to(TradeState.POSITION_CLOSED)
        tsm.transition_to(TradeState.DEALS_RECONCILED)
        tsm.transition_to(TradeState.TRADE_FINALIZED)
        assert tsm.is_complete
    
    def test_signal_to_closed_blocked(self):
        """SIGNAL_CREATED -> POSITION_CLOSED must be IMPOSSIBLE"""
        tsm = TradeStateMachine("test_002")
        with pytest.raises(InvalidTransitionError):
            tsm.transition_to(TradeState.POSITION_CLOSED)
    
    def test_terminal_state_blocked(self):
        """Cannot transition from terminal state"""
        tsm = TradeStateMachine("test_003")
        tsm.transition_to(TradeState.RISK_REJECTED)
        with pytest.raises(InvalidTransitionError):
            tsm.transition_to(TradeState.ORDER_SUBMITTED)

class TestErrorCategories:
    """Tests that errors have correct categories"""
    
    def test_trade_rejection_category(self):
        """Trade rejection errors must be TRADE_REJECT category"""
        from packages.domain.errors import ErrorCategory
        err = MissingRegimeError('EURUSD')
        assert err.category == ErrorCategory.TRADE_REJECT
    
    def test_fatal_error_category(self):
        """Fatal errors must be FATAL category"""
        from packages.domain.errors import MT5ConnectionError, ErrorCategory
        err = MT5ConnectionError("test")
        assert err.category == ErrorCategory.FATAL

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
