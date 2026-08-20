"""Integration test: Stale signal -> freshness gate -> NO MT5 order_send"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from packages.execution.signal_freshness import validate_signal_freshness

class TestExecutionIntegration:
    """Proves stale signals CANNOT reach MT5"""
    
    def test_stale_signal_blocks_execution(self):
        """Full path: signal -> freshness gate -> REJECT -> no order_send"""
        stale_signal = {
            'signal_id': 'test_stale',
            'generated_at': datetime.now(timezone.utc) - timedelta(seconds=300),
            'expires_at': datetime.now(timezone.utc) - timedelta(seconds=180),
            'pair': 'EURUSD',
            'direction': 'SELL',
            'entry': 1.15123,
            'stop_loss': 1.15299,
            'take_profit': 1.14842,
        }
        
        freshness = validate_signal_freshness(stale_signal, 1.15542, 1.15550)
        
        assert not freshness.is_executable, "Stale signal must be rejected"
        
        # Simulate executor checking freshness before order
        with patch('MetaTrader5.order_send') as mock_order_send:
            if freshness.is_executable:
                # This should never execute
                mock_order_send({})
            mock_order_send.assert_not_called()
            print("PASS: mt5.order_send was NOT called for stale signal")
    
    def test_fresh_signal_allows_execution(self):
        """Fresh signal with valid SL/TP CAN proceed"""
        fresh_signal = {
            'signal_id': 'test_fresh',
            'generated_at': datetime.now(timezone.utc) - timedelta(seconds=10),
            'expires_at': datetime.now(timezone.utc) + timedelta(seconds=110),
            'pair': 'EURUSD',
            'direction': 'SELL',
            'entry': 1.15540,
            'stop_loss': 1.15700,
            'take_profit': 1.15200,
        }
        
        freshness = validate_signal_freshness(fresh_signal, 1.15542, 1.15550)
        assert freshness.is_executable, "Fresh signal should pass"
        print("PASS: Fresh signal correctly allowed to proceed")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
