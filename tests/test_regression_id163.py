"""Permanent regression tests for ID 163 execution failure.
These tests ensure the system NEVER repeats this failure mode.
If anyone modifies the execution engine and these fail, CI must block deployment.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from datetime import datetime, timezone, timedelta
from packages.execution.signal_freshness import validate_signal_freshness, MAX_SIGNAL_AGE_SECONDS, MAX_ENTRY_DEVIATION_PIPS

class TestRegressionID163:
    """ID 163: Stale signal (1.15123) executed at wrong price (1.15542) with invalid SL"""
    
    def stale_signal_fixture(self):
        """Recreate the exact conditions that produced ID 163"""
        return {
            'signal_id': 'EURUSD_SELL_163',
            'generated_at': datetime.now(timezone.utc) - timedelta(seconds=300),
            'expires_at': datetime.now(timezone.utc) - timedelta(seconds=180),
            'pair': 'EURUSD',
            'direction': 'SELL',
            'entry': 1.15123,      # Stale cached price
            'stop_loss': 1.15299,  # Invalid for actual fill
            'take_profit': 1.14842,
        }
    
    def test_stale_signal_rejected(self):
        """ID 163 had a 300s old signal - MUST be rejected"""
        signal = self.stale_signal_fixture()
        freshness = validate_signal_freshness(signal, 1.15542, 1.15550)
        assert not freshness.is_fresh, "300s old signal must be detected as stale"
        assert freshness.signal_age_seconds > MAX_SIGNAL_AGE_SECONDS
        assert "STALE_SIGNAL" in str(freshness.issues)
    
    def test_extreme_deviation_rejected(self):
        """ID 163 had 41.9 pip deviation - MUST be rejected"""
        signal = self.stale_signal_fixture()
        freshness = validate_signal_freshness(signal, 1.15542, 1.15550)
        assert not freshness.entry_acceptable, "41.9 pip deviation must be rejected"
        assert freshness.entry_deviation_pips > MAX_ENTRY_DEVIATION_PIPS
        assert "EXTREME_DEVIATION" in str(freshness.issues)
    
    def test_invalid_sl_rejected_for_actual_fill(self):
        """ID 163 SL (1.15299) was below actual entry (1.15542) for SELL - INVALID"""
        signal = self.stale_signal_fixture()
        # If the stale signal were used: SL(1.15299) > Entry(1.15123) = VALID for SELL
        # But with actual fill: SL(1.15299) < Entry(1.15542) = INVALID for SELL
        freshness = validate_signal_freshness(signal, 1.15542, 1.15550)
        assert not freshness.is_executable, "Invalid SL must block execution"
    
    def test_recalculated_sl_valid_for_current_market(self):
        """After recalculation, SL must be valid for current market price"""
        signal = self.stale_signal_fixture()
        freshness = validate_signal_freshness(signal, 1.15542, 1.15550)
        # Recalculated SL should be above entry for SELL
        assert freshness.recalculated_sl > freshness.current_entry, \
            f"Recalculated SL {freshness.recalculated_sl} must be above entry {freshness.current_entry}"
        assert freshness.sl_valid, "Recalculated SL must be valid"
    
    def test_recalculated_tp_valid_for_current_market(self):
        """After recalculation, TP must be valid for current market price"""
        signal = self.stale_signal_fixture()
        freshness = validate_signal_freshness(signal, 1.15542, 1.15550)
        # Recalculated TP should be below entry for SELL
        assert freshness.recalculated_tp < freshness.current_entry, \
            f"Recalculated TP {freshness.recalculated_tp} must be below entry {freshness.current_entry}"
        assert freshness.tp_valid, "Recalculated TP must be valid"
    
    def test_overall_execution_blocked(self):
        """The complete ID 163 scenario must be BLOCKED"""
        signal = self.stale_signal_fixture()
        freshness = validate_signal_freshness(signal, 1.15542, 1.15550)
        assert not freshness.is_executable, \
            "ID 163 scenario must be completely blocked from execution"
    
    def test_fresh_signal_with_small_deviation_passes(self):
        """A fresh signal with acceptable deviation SHOULD pass"""
        fresh_signal = {
            'signal_id': 'EURUSD_SELL_FRESH',
            'generated_at': datetime.now(timezone.utc) - timedelta(seconds=10),
            'expires_at': datetime.now(timezone.utc) + timedelta(seconds=110),
            'pair': 'EURUSD',
            'direction': 'SELL',
            'entry': 1.15540,
            'stop_loss': 1.15700,
            'take_profit': 1.15200,
        }
        freshness = validate_signal_freshness(fresh_signal, 1.15542, 1.15550)
        assert freshness.is_executable, \
            f"Fresh signal should pass. Issues: {freshness.issues}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
