"""Fail-Closed Enforcer - Every uncertainty = NO TRADE.
When in doubt, the system does NOT trade. Never fails open.
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class UncertaintyType(str, Enum):
    MT5_STATE_UNKNOWN = "MT5_STATE_UNKNOWN"
    ACCOUNT_IDENTITY_UNKNOWN = "ACCOUNT_IDENTITY_UNKNOWN"
    RECONCILIATION_UNKNOWN = "RECONCILIATION_UNKNOWN"
    RISK_CALCULATION_UNKNOWN = "RISK_CALCULATION_UNKNOWN"
    SIGNAL_FRESHNESS_UNKNOWN = "SIGNAL_FRESHNESS_UNKNOWN"
    POSITION_STATE_UNKNOWN = "POSITION_STATE_UNKNOWN"

@dataclass
class FailClosedResult:
    """Result of fail-closed check"""
    can_trade: bool
    uncertainty: Optional[UncertaintyType] = None
    detail: str = ""

class FailClosedEnforcer:
    """Enforces fail-closed behavior. ANY uncertainty = NO TRADE."""
    
    def check_mt5_state(self, mt5_connected: bool, account_info_available: bool) -> FailClosedResult:
        """MT5 state must be fully known"""
        if not mt5_connected:
            return FailClosedResult(False, UncertaintyType.MT5_STATE_UNKNOWN, 
                                   "MT5 not connected - NO TRADE")
        if not account_info_available:
            return FailClosedResult(False, UncertaintyType.MT5_STATE_UNKNOWN,
                                   "MT5 account info unavailable - NO TRADE")
        return FailClosedResult(True)
    
    def check_account_identity(self, expected_account_id: int, 
                               actual_account_id: Optional[int]) -> FailClosedResult:
        """Account identity must match exactly"""
        if actual_account_id is None:
            return FailClosedResult(False, UncertaintyType.ACCOUNT_IDENTITY_UNKNOWN,
                                   "Account ID unknown - NO TRADE")
        if actual_account_id != expected_account_id:
            return FailClosedResult(False, UncertaintyType.ACCOUNT_IDENTITY_UNKNOWN,
                                   f"Account mismatch: expected {expected_account_id}, got {actual_account_id} - NO TRADE")
        return FailClosedResult(True)
    
    def check_reconciliation(self, db_pnl: Optional[float], 
                             mt5_pnl: Optional[float]) -> FailClosedResult:
        """Reconciliation must be exact"""
        if db_pnl is None or mt5_pnl is None:
            return FailClosedResult(False, UncertaintyType.RECONCILIATION_UNKNOWN,
                                   "Cannot reconcile PnL - NO TRADE")
        if abs(db_pnl - mt5_pnl) > 0.01:
            return FailClosedResult(False, UncertaintyType.RECONCILIATION_UNKNOWN,
                                   f"PnL mismatch: DB={db_pnl} vs MT5={mt5_pnl} - NO TRADE")
        return FailClosedResult(True)
    
    def check_risk_calculation(self, risk_amount: Optional[float], 
                               risk_budget: Optional[float]) -> FailClosedResult:
        """Risk must be calculable"""
        if risk_amount is None or risk_budget is None:
            return FailClosedResult(False, UncertaintyType.RISK_CALCULATION_UNKNOWN,
                                   "Risk cannot be calculated - NO TRADE")
        if risk_amount > risk_budget:
            return FailClosedResult(False, UncertaintyType.RISK_CALCULATION_UNKNOWN,
                                   f"Risk ${risk_amount:.2f} exceeds budget ${risk_budget:.4f} - NO TRADE")
        return FailClosedResult(True)
    
    def check_signal_freshness(self, signal_age_seconds: Optional[float],
                               max_age: float = 120.0) -> FailClosedResult:
        """Signal must be fresh"""
        if signal_age_seconds is None:
            return FailClosedResult(False, UncertaintyType.SIGNAL_FRESHNESS_UNKNOWN,
                                   "Signal age unknown - NO TRADE")
        if signal_age_seconds > max_age:
            return FailClosedResult(False, UncertaintyType.SIGNAL_FRESHNESS_UNKNOWN,
                                   f"Signal {signal_age_seconds:.0f}s old - NO TRADE")
        return FailClosedResult(True)
    
    def check_position_state(self, position_exists: bool, 
                             position_verified: bool) -> FailClosedResult:
        """Position must be verified"""
        if not position_exists:
            return FailClosedResult(False, UncertaintyType.POSITION_STATE_UNKNOWN,
                                   "Position does not exist - NO TRADE")
        if not position_verified:
            return FailClosedResult(False, UncertaintyType.POSITION_STATE_UNKNOWN,
                                   "Position not verified - NO TRADE")
        return FailClosedResult(True)


# ============================================================================
# TEST - Prove fail-closed behavior
# ============================================================================
if __name__ == "__main__":
    print("=" * 65)
    print("  FAIL-CLOSED TEST - Any Uncertainty = NO TRADE")
    print("=" * 65)
    
    enforcer = FailClosedEnforcer()
    
    tests = [
        ("MT5 connected + account info", enforcer.check_mt5_state(True, True)),
        ("MT5 NOT connected", enforcer.check_mt5_state(False, True)),
        ("Account identity matches", enforcer.check_account_identity(REDACTED_LIVE_ACCOUNT, REDACTED_LIVE_ACCOUNT)),
        ("Account MISMATCH", enforcer.check_account_identity(REDACTED_LIVE_ACCOUNT, REDACTED_DEMO_ACCOUNT)),
        ("Account UNKNOWN", enforcer.check_account_identity(REDACTED_LIVE_ACCOUNT, None)),
        ("Reconciliation matches", enforcer.check_reconciliation(-0.13, -0.13)),
        ("Reconciliation MISMATCH", enforcer.check_reconciliation(-0.13, -8.10)),
        ("Risk calculable + within budget", enforcer.check_risk_calculation(1.76, 2.50)),
        ("Risk EXCEEDS budget", enforcer.check_risk_calculation(176.00, 0.0095)),
        ("Signal fresh (10s)", enforcer.check_signal_freshness(10)),
        ("Signal STALE (300s)", enforcer.check_signal_freshness(300)),
        ("Position exists + verified", enforcer.check_position_state(True, True)),
        ("Position NOT verified", enforcer.check_position_state(True, False)),
    ]
    
    for name, result in tests:
        icon = "TRADE" if result.can_trade else "NO TRADE"
        print(f"  [{icon}] {name}")
    
    print(f"\n{'='*65}")
    print("  PRINCIPLE: FAIL CLOSED - When in doubt, NO TRADE")
    print("  Never fail open. Never trade on uncertainty.")
    print(f"{'='*65}")
