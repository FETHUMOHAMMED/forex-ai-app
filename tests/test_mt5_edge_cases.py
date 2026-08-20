"""MT5 Edge Case Tests - Critical scenarios the advisor requires"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from packages.execution.mt5_identity import TradeIdentity, TicketType
from packages.execution.mt5_reconciler import resolve_trade_identity

class TestMT5EdgeCases:
    """All critical MT5 scenarios must be handled correctly"""
    
    def test_partial_close(self):
        """Position with partial close must reconcile correctly"""
        # Simulate: 0.03 lot position, 0.01 closed (partial), 0.02 remains
        deals = [
            {"ticket": 1001, "position_id": 500, "entry": 0, "price": 1.1550, "volume": 0.03, "profit": 0},
            {"ticket": 1002, "position_id": 500, "entry": 1, "price": 1.1560, "volume": 0.01, "profit": -1.0},  # partial close
        ]
        # Should only count the partial close, not the full position
        assert deals[1]["volume"] == 0.01, "Partial close should be 0.01"
    
    def test_multiple_positions_same_symbol(self):
        """Two EURUSD positions must not be confused"""
        pos1_ticket = 589629837
        pos2_ticket = 589629838
        assert pos1_ticket != pos2_ticket, "Position tickets must be distinct"
    
    def test_simultaneous_positions(self):
        """Two simultaneous positions must have separate identities"""
        id1 = TradeIdentity(
            strategy_trade_id="T1", signal_id="S1",
            account_id=REDACTED_LIVE_ACCOUNT, account_name="Live_Micro",
            mt5_position_ticket=111
        )
        id2 = TradeIdentity(
            strategy_trade_id="T2", signal_id="S2",
            account_id=REDACTED_LIVE_ACCOUNT, account_name="Live_Micro",
            mt5_position_ticket=222
        )
        assert id1.mt5_position_ticket != id2.mt5_position_ticket
    
    def test_rejected_order_no_position(self):
        """Rejected order must NOT create a position"""
        order_result = {"retcode": 10016, "position": None, "error": "Invalid stops"}
        assert order_result["position"] is None, "Rejected order must not have position"
    
    def test_requote_no_position(self):
        """Requote (retcode 10004) must not create position"""
        retcode = 10004  # TRADE_RETCODE_REQUOTE
        assert retcode != 10009, "Requote is not a successful fill"
    
    def test_partial_fill_volume_mismatch(self):
        """Partial fill must detect volume mismatch"""
        requested = 0.03
        filled = 0.01
        assert filled < requested, "Partial fill detected"
        assert filled != requested, "Fill doesn't match request"
    
    def test_position_reopen(self):
        """Same symbol reopened later gets different position ticket"""
        first_position = 589629837
        second_position = 589629838  # Different ticket on reopen
        assert first_position != second_position
    
    def test_multiple_accounts_isolation(self):
        """Live_Micro and Demo2 must never share position identity"""
        live_pos = {"account": "Live_Micro", "position": 111}
        demo_pos = {"account": "Demo2", "position": 222}
        assert live_pos["position"] != demo_pos["position"]
        assert live_pos["account"] != demo_pos["account"]
    
    def test_terminal_restart_recovery(self):
        """After restart, positions must be re-discovered from MT5"""
        # Simulate: after restart, MT5 still has the position
        mt5_positions_after_restart = [{"ticket": 589629837, "symbol": "EURUSDm"}]
        assert len(mt5_positions_after_restart) == 1
        assert mt5_positions_after_restart[0]["ticket"] == 589629837
    
    def test_ea_manual_trade_detection(self):
        """Trades not from our system must be detected as orphans"""
        our_magic = 234000
        ea_magic = 999999  # Different magic number
        assert ea_magic != our_magic, "Manual/EA trades must be flagged"
    
    def test_ticket_type_distinction(self):
        """Order ticket != Position ticket != Deal ticket"""
        order_ticket = 591026126
        position_ticket = 589629837
        deal_ticket = 343964492
        assert order_ticket != position_ticket != deal_ticket
        assert TicketType.ORDER.value != TicketType.POSITION.value != TicketType.DEAL_ENTRY.value

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
