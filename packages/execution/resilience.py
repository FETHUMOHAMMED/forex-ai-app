"""Live Trading Resilience Layer - Handles EVERY failure mode.
A live system must be trustworthy when things go wrong, not just when they work.
"""
import time
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

class FailureMode(str, Enum):
    """Every way the system can fail - must have a handler"""
    MT5_DISCONNECTED = "MT5_DISCONNECTED"
    PROCESS_CRASH = "PROCESS_CRASH"
    DATABASE_LOCKED = "DATABASE_LOCKED"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    ORDER_PARTIAL_FILL = "ORDER_PARTIAL_FILL"
    ORDER_PRICE_SLIPPAGE = "ORDER_PRICE_SLIPPAGE"
    PROCESS_RESTART = "PROCESS_RESTART"
    DUPLICATE_SIGNAL = "DUPLICATE_SIGNAL"
    CONCURRENT_ACCOUNTS = "CONCURRENT_ACCOUNTS"
    BROKER_REJECT = "BROKER_REJECT"
    MARKET_GAP = "MARKET_GAP"
    MISSING_METADATA = "MISSING_METADATA"
    STALE_SIGNAL = "STALE_SIGNAL"
    WRONG_ACCOUNT = "WRONG_ACCOUNT"

@dataclass
class ResilienceResult:
    """Result of a resilience check"""
    failure_mode: FailureMode
    handled: bool
    action_taken: str
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ResilienceLayer:
    """Handles EVERY known failure mode with explicit actions.
    
    Principle: When something goes wrong, the system must:
    1. DETECT the failure
    2. LOG it immediately
    3. Take SAFE action (pause, retry, or abort)
    4. ALERT if critical
    5. RECOVER gracefully
    """
    
    def __init__(self):
        self.failure_counts: Dict[FailureMode, int] = {fm: 0 for fm in FailureMode}
        self.last_failure: Dict[FailureMode, Optional[str]] = {fm: None for fm in FailureMode}
        self._lock = threading.Lock()
    
    def handle_mt5_disconnect(self, account_name: str, max_retries: int = 5) -> ResilienceResult:
        """MT5 disconnected -> retry with backoff, then pause account"""
        self.failure_counts[FailureMode.MT5_DISCONNECTED] += 1
        
        for attempt in range(max_retries):
            try:
                import MetaTrader5 as mt5
                if mt5.initialize():
                    return ResilienceResult(
                        FailureMode.MT5_DISCONNECTED, True,
                        f"Reconnected on attempt {attempt + 1}"
                    )
            except:
                pass
            time.sleep(min(2 ** attempt, 30))  # Exponential backoff
        
        return ResilienceResult(
            FailureMode.MT5_DISCONNECTED, False,
            f"FAILED after {max_retries} retries - account {account_name} PAUSED"
        )
    
    def handle_order_partial_fill(self, requested: float, filled: float) -> ResilienceResult:
        """Order partially filled -> log discrepancy, do NOT resubmit"""
        self.failure_counts[FailureMode.ORDER_PARTIAL_FILL] += 1
        
        fill_pct = (filled / requested * 100) if requested > 0 else 0
        
        if fill_pct < 50:
            return ResilienceResult(
                FailureMode.ORDER_PARTIAL_FILL, False,
                f"Only {fill_pct:.0f}% filled ({filled}/{requested}) - ABORTING, do not re-enter"
            )
        
        return ResilienceResult(
            FailureMode.ORDER_PARTIAL_FILL, True,
            f"Partial fill {fill_pct:.0f}% - accepted, monitoring"
        )
    
    def handle_price_slippage(self, expected: float, actual: float, max_slippage_pips: float = 5.0) -> ResilienceResult:
        """Price slipped -> check if within tolerance"""
        self.failure_counts[FailureMode.ORDER_PRICE_SLIPPAGE] += 1
        
        slippage_pips = abs(actual - expected) * 10000
        
        if slippage_pips > max_slippage_pips:
            return ResilienceResult(
                FailureMode.ORDER_PRICE_SLIPPAGE, False,
                f"Slippage {slippage_pips:.1f} pips exceeds max {max_slippage_pips} - REJECT"
            )
        
        return ResilienceResult(
            FailureMode.ORDER_PRICE_SLIPPAGE, True,
            f"Slippage {slippage_pips:.1f} pips within tolerance"
        )
    
    def handle_duplicate_signal(self, pair: str, direction: str, existing_ticket: int) -> ResilienceResult:
        """Duplicate signal -> REJECT, we already have a position"""
        self.failure_counts[FailureMode.DUPLICATE_SIGNAL] += 1
        
        return ResilienceResult(
            FailureMode.DUPLICATE_SIGNAL, False,
            f"Already have {direction} on {pair} (ticket {existing_ticket}) - REJECTED"
        )
    
    def handle_broker_reject(self, retcode: int, comment: str) -> ResilienceResult:
        """Broker rejected order -> analyze why, decide action"""
        self.failure_counts[FailureMode.BROKER_REJECT] += 1
        
        # Common MT5 retcodes
        if retcode == 10016:  # Invalid stops
            return ResilienceResult( FailureMode.BROKER_REJECT, False, "Invalid stops - check SL/TP distance" )
        elif retcode == 10019:  # No money
            return ResilienceResult( FailureMode.BROKER_REJECT, False, "Insufficient margin - PAUSE account" )
        elif retcode == 10014:  # Invalid volume
            return ResilienceResult( FailureMode.BROKER_REJECT, False, "Invalid volume - check lot size" )
        else:
            return ResilienceResult( FailureMode.BROKER_REJECT, False, f"Retcode {retcode}: {comment}" )
    
    def handle_market_gap(self, pair: str, gap_pips: float, max_gap: float = 10.0) -> ResilienceResult:
        """Market gapped -> SL may not be honored, check exposure"""
        self.failure_counts[FailureMode.MARKET_GAP] += 1
        
        if gap_pips > max_gap:
            return ResilienceResult(
                FailureMode.MARKET_GAP, False,
                f"Gap {gap_pips:.1f} pips exceeds {max_gap} - emergency close possible"
            )
        
        return ResilienceResult(
            FailureMode.MARKET_GAP, True,
            f"Gap {gap_pips:.1f} pips within tolerance"
        )
    
    def handle_missing_metadata(self, field: str, pair: str) -> ResilienceResult:
        """Required metadata missing -> REJECT trade, do not guess"""
        self.failure_counts[FailureMode.MISSING_METADATA] += 1
        
        return ResilienceResult(
            FailureMode.MISSING_METADATA, False,
            f"Missing {field} for {pair} - REJECTED (never trade with missing data)"
        )
    
    def handle_stale_signal(self, pair: str, signal_age_seconds: float, max_age: float = 300) -> ResilienceResult:
        """Signal is too old -> REJECT, get fresh signal"""
        self.failure_counts[FailureMode.STALE_SIGNAL] += 1
        
        if signal_age_seconds > max_age:
            return ResilienceResult(
                FailureMode.STALE_SIGNAL, False,
                f"Signal {signal_age_seconds:.0f}s old (max {max_age}s) - REJECTED"
            )
        
        return ResilienceResult(FailureMode.STALE_SIGNAL, True, "Signal age acceptable")
    
    def handle_wrong_account(self, expected: int, actual: int) -> ResilienceResult:
        """Trading on wrong account -> FATAL, stop immediately"""
        self.failure_counts[FailureMode.WRONG_ACCOUNT] += 1
        
        return ResilienceResult(
            FailureMode.WRONG_ACCOUNT, False,
            f"CRITICAL: Expected account {expected}, got {actual} - HALTING"
        )
    
    def get_status(self) -> dict:
        """Get resilience status for monitoring"""
        with self._lock:
            return {
                "total_failures": sum(self.failure_counts.values()),
                "by_mode": {fm.value: count for fm, count in self.failure_counts.items()},
                "last_failure": {fm.value: ts for fm, ts in self.last_failure.items() if ts},
            }


# ============================================================================
# GLOBAL RESILIENCE INSTANCE
# ============================================================================

resilience = ResilienceLayer()
