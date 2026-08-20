"""Domain Invariants - Automated enforcement of data integrity rules.
Replaces the pattern: detect problem -> write script -> manually repair
With:            domain invariant -> automated enforcement -> automated alert
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timezone

@dataclass
class InvariantViolation:
    """A single data integrity violation"""
    rule: str
    severity: str  # CRITICAL, ERROR, WARNING
    field: str
    expected: str
    actual: str
    trade_id: Optional[int] = None
    detail: str = ""

class TradeInvariants:
    """Enforce data integrity at trade creation, update, and close time.
    
    Usage:
        violations = TradeInvariants.validate_on_open(trade_data)
        if violations:
            for v in violations:
                logger.error(f"[INVARIANT] {v.severity}: {v.rule} - {v.detail}")
            raise DataIntegrityError(violations)
    """
    
    @staticmethod
    def validate_on_open(trade: dict) -> List[InvariantViolation]:
        """Check invariants BEFORE inserting a new trade.
        Call this in log_trade_entry() before the INSERT.
        """
        v = []
        
        # CRITICAL: Must have MT5 position ID
        if not trade.get('mt5_position_id'):
            v.append(InvariantViolation(
                rule="MUST_HAVE_MT5_POSITION",
                severity="CRITICAL",
                field="mt5_position_id",
                expected="valid MT5 position ID",
                actual="None or empty",
                detail="Trade must have a verified MT5 position ID before DB insertion"
            ))
        
        # CRITICAL: Entry price must differ from stale signal default
        if trade.get('entry') == 1.15123:
            v.append(InvariantViolation(
                rule="ENTRY_NOT_STALE_SIGNAL",
                severity="CRITICAL",
                field="entry",
                expected="actual MT5 fill price",
                actual="1.15123 (stale signal default)",
                detail="Entry price must be actual MT5 execution price, not cached signal price"
            ))
        
        # CRITICAL: Account name must match account_id
        if trade.get('account') == 'Live_Micro' and trade.get('account_name') == 'Demo2':
            v.append(InvariantViolation(
                rule="ACCOUNT_NAME_CONSISTENT",
                severity="CRITICAL",
                field="account_name",
                expected="Live_Micro",
                actual="Demo2",
                detail="account_name must match account field"
            ))
        
        # CRITICAL: Must have strategy_version
        if trade.get('strategy_version') in (None, '', 'PRE_V3'):
            v.append(InvariantViolation(
                rule="STRATEGY_VERSION_REQUIRED",
                severity="CRITICAL",
                field="strategy_version",
                expected="V3_REGIME or similar",
                actual=str(trade.get('strategy_version')),
                detail="strategy_version must be explicitly set"
            ))
        
        # ERROR: Timestamp must have timezone
        ts = trade.get('timestamp', '')
        if ts and '+' not in ts and 'Z' not in ts:
            v.append(InvariantViolation(
                rule="TIMESTAMP_HAS_TIMEZONE",
                severity="ERROR",
                field="timestamp",
                expected="ISO 8601 with timezone",
                actual=ts,
                detail="All timestamps must include UTC offset (+00:00 or Z)"
            ))
        
        # ERROR: Volume must be reasonable for account
        vol = trade.get('volume', 0)
        if vol >= 1.0 and trade.get('account') == 'Live_Micro':
            v.append(InvariantViolation(
                rule="VOLUME_REASONABLE_FOR_ACCOUNT",
                severity="ERROR",
                field="volume",
                expected="<= 0.01 for Live_Micro",
                actual=str(vol),
                detail=f"Volume {vol} lots too large for Live_Micro account"
            ))
        
        # WARNING: Environment should match trade_mode
        env = trade.get('environment', '')
        mode = trade.get('trade_mode', '')
        if 'VALIDATION' in str(env).upper() and mode == 'PRODUCTION':
            v.append(InvariantViolation(
                rule="MODE_ENVIRONMENT_CONSISTENT",
                severity="WARNING",
                field="trade_mode",
                expected="VALIDATION",
                actual=mode,
                detail="trade_mode should be VALIDATION when environment is LIVE_MICRO_VALIDATION"
            ))
        
        return v
    
    @staticmethod
    def validate_on_close(trade: dict) -> List[InvariantViolation]:
        """Check invariants BEFORE closing a trade.
        Call this in log_trade_exit() before the UPDATE.
        """
        v = []
        
        # CRITICAL: Exit time must be after entry time
        entry_time = trade.get('opened_at_utc')
        exit_time = trade.get('closed_at_utc')
        if entry_time and exit_time:
            if isinstance(entry_time, str):
                entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            if isinstance(exit_time, str):
                exit_time = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            if exit_time < entry_time:
                v.append(InvariantViolation(
                    rule="EXIT_AFTER_ENTRY",
                    severity="CRITICAL",
                    field="exit_time",
                    expected=f"after {entry_time}",
                    actual=str(exit_time),
                    trade_id=trade.get('id'),
                    detail=f"Exit time {exit_time} is BEFORE entry time {entry_time}"
                ))
        
        # ERROR: Must have PnL when closing
        if trade.get('pnl') is None and trade.get('exit_price') is not None:
            v.append(InvariantViolation(
                rule="PNL_REQUIRED_ON_CLOSE",
                severity="ERROR",
                field="pnl",
                expected="calculated PnL value",
                actual="None",
                trade_id=trade.get('id'),
                detail="PnL must be calculated and stored when trade closes"
            ))
        
        # ERROR: Must have exit price
        if trade.get('exit_price') is None:
            v.append(InvariantViolation(
                rule="EXIT_PRICE_REQUIRED",
                severity="ERROR",
                field="exit_price",
                expected="MT5 deal close price",
                actual="None",
                trade_id=trade.get('id'),
                detail="exit_price must be set when closing a trade"
            ))
        
        return v
    
    @staticmethod
    def validate_for_stats(trade: dict) -> List[InvariantViolation]:
        """Check if a closed trade is valid for statistical analysis."""
        v = []
        
        # Must pass all on-open and on-close checks
        v.extend(TradeInvariants.validate_on_open(trade))
        v.extend(TradeInvariants.validate_on_close(trade))
        
        # Additional stats-specific checks
        if trade.get('result') == 'PHANTOM':
            v.append(InvariantViolation(
                rule="NOT_PHANTOM",
                severity="CRITICAL",
                field="result",
                expected="WIN/LOSS/BREAKEVEN",
                actual="PHANTOM",
                trade_id=trade.get('id'),
                detail="Phantom trades must not be included in statistics"
            ))
        
        if trade.get('entry') == trade.get('planned_entry') == 1.15123:
            v.append(InvariantViolation(
                rule="ENTRY_NOT_STALE",
                severity="ERROR",
                field="entry",
                expected="unique execution price",
                actual="1.15123 (stale cache)",
                trade_id=trade.get('id'),
                detail="Entry price matches known stale signal cache value"
            ))
        
        return v


class DataIntegrityError(Exception):
    """Raised when trade invariants are violated"""
    def __init__(self, violations: List[InvariantViolation]):
        self.violations = violations
        msg = "\n".join(f"[{v.severity}] {v.rule}: {v.detail}" for v in violations)
        super().__init__(f"Data integrity violations:\n{msg}")


def enforce_invariants(violations: List[InvariantViolation], 
                        on_critical: str = "raise",
                        on_error: str = "log_and_raise",
                        on_warning: str = "log"):
    """Enforce invariants based on severity.
    
    Args:
        violations: List of InvariantViolation objects
        on_critical: Action for CRITICAL - "raise" or "log"
        on_error: Action for ERROR - "raise", "log_and_raise", or "log"
        on_warning: Action for WARNING - "log" or "ignore"
    
    Raises:
        DataIntegrityError: If any CRITICAL or ERROR violations with raise action
    """
    critical = [v for v in violations if v.severity == "CRITICAL"]
    errors = [v for v in violations if v.severity == "ERROR"]
    warnings = [v for v in violations if v.severity == "WARNING"]
    
    for w in warnings:
        if on_warning == "log":
            print(f"[INVARIANT WARNING] {w.rule}: {w.detail}")
    
    for e in errors:
        if on_error in ("log", "log_and_raise"):
            print(f"[INVARIANT ERROR] {e.rule}: {e.detail}")
    
    for c in critical:
        if on_critical in ("raise",):
            print(f"[INVARIANT CRITICAL] {c.rule}: {c.detail}")
    
    should_raise = []
    if on_critical == "raise":
        should_raise.extend(critical)
    if on_error in ("raise", "log_and_raise"):
        should_raise.extend(errors)
    
    if should_raise:
        raise DataIntegrityError(should_raise)
