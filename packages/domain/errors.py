"""Fail-Fast Error Handling for Financial Software.
Missing metadata = REJECT TRADE, not continue with UNKNOWN.
"""
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

class ErrorCategory(str, Enum):
    """Categorize every error by severity and required action"""
    FATAL = "FATAL"           # System must stop - cannot continue safely
    TRADE_REJECT = "TRADE_REJECT"  # Reject this trade, continue scanning
    ACCOUNT_PAUSE = "ACCOUNT_PAUSE"  # Pause this account, continue others
    RETRY = "RETRY"           # Temporary failure, retry with backoff
    DEGRADED = "DEGRADED"     # Continue with reduced functionality
    WARNING = "WARNING"       # Log but continue

class ForexError(Exception):
    """Base exception for all FOREX-AI-APP errors"""
    def __init__(self, message: str, category: ErrorCategory, 
                 detail: Optional[Dict[str, Any]] = None):
        self.category = category
        self.detail = detail or {}
        super().__init__(f"[{category.value}] {message}")

# ============================================================================
# FATAL ERRORS - System must stop
# ============================================================================

class MT5ConnectionError(ForexError):
    """MT5 terminal not available - cannot trade"""
    def __init__(self, detail: str = ""):
        super().__init__("MT5 connection failed", ErrorCategory.FATAL, 
                        {"reason": detail})

class DatabaseCorruptionError(ForexError):
    """Database integrity compromised"""
    def __init__(self, detail: str = ""):
        super().__init__("Database corruption detected", ErrorCategory.FATAL,
                        {"reason": detail})

class AccountMismatchError(ForexError):
    """Trading on wrong account"""
    def __init__(self, expected: int, actual: int):
        super().__init__(f"Wrong account: expected {expected}, got {actual}",
                        ErrorCategory.FATAL,
                        {"expected_account": expected, "actual_account": actual})

# ============================================================================
# TRADE REJECTION ERRORS - Missing metadata = reject trade
# ============================================================================

class TradeRejectionError(ForexError):
    """Base class for trade rejections - trade is blocked"""
    def __init__(self, message: str, detail: Optional[Dict] = None):
        super().__init__(message, ErrorCategory.TRADE_REJECT, detail)

class MissingRegimeError(TradeRejectionError):
    """Regime is UNKNOWN or missing - REJECT TRADE"""
    def __init__(self, pair: str):
        super().__init__(f"Missing regime for {pair} - rejecting trade",
                        {"pair": pair, "missing_field": "regime"})

class MissingConfidenceError(TradeRejectionError):
    """Confidence score missing or invalid"""
    def __init__(self, pair: str, confidence: Optional[float]):
        super().__init__(f"Invalid confidence {confidence} for {pair}",
                        {"pair": pair, "confidence": confidence})

class MissingMetadataError(TradeRejectionError):
    """Required metadata field is missing"""
    def __init__(self, field: str, pair: str):
        super().__init__(f"Missing required metadata: {field} for {pair}",
                        {"missing_field": field, "pair": pair})

class StaleSignalError(TradeRejectionError):
    """Signal price matches known stale cache value"""
    def __init__(self, pair: str, price: float):
        super().__init__(f"Stale signal price {price} for {pair}",
                        {"pair": pair, "price": price})

class RiskViolationError(TradeRejectionError):
    """Risk parameters violated"""
    def __init__(self, reason: str, actual_risk: float, max_risk: float):
        super().__init__(f"Risk violation: {reason}",
                        {"actual_risk": actual_risk, "max_risk": max_risk,
                         "reason": reason})

class LotSizeError(TradeRejectionError):
    """Lot size out of bounds"""
    def __init__(self, volume: float, min_vol: float, max_vol: float):
        super().__init__(f"Invalid lot size {volume} (min={min_vol}, max={max_vol})",
                        {"volume": volume, "min": min_vol, "max": max_vol})

class SessionFilterError(TradeRejectionError):
    """Outside trading session"""
    def __init__(self, pair: str, current_hour: int):
        super().__init__(f"{pair} outside trading session (hour={current_hour})",
                        {"pair": pair, "hour": current_hour})

class SpreadError(TradeRejectionError):
    """Spread too wide"""
    def __init__(self, pair: str, spread: float, max_spread: float):
        super().__init__(f"Spread {spread:.6f} exceeds max {max_spread:.6f} for {pair}",
                        {"pair": pair, "spread": spread, "max": max_spread})

class DuplicateTradeError(TradeRejectionError):
    """Already have a position in this direction"""
    def __init__(self, pair: str, direction: str):
        super().__init__(f"Duplicate {direction} on {pair}",
                        {"pair": pair, "direction": direction})

class DailyLimitError(TradeRejectionError):
    """Daily trade limit reached"""
    def __init__(self, current: int, max_limit: int):
        super().__init__(f"Daily limit reached: {current}/{max_limit}",
                        {"current": current, "max": max_limit})

# ============================================================================
# DATA INTEGRITY ERRORS
# ============================================================================

class DataIntegrityError(ForexError):
    """Data does not match between sources"""
    def __init__(self, message: str, db_value: Any, mt5_value: Any):
        super().__init__(message, ErrorCategory.DEGRADED,
                        {"db_value": str(db_value), "mt5_value": str(mt5_value)})

class PhantomTradeError(DataIntegrityError):
    """Trade exists in DB but not in MT5"""
    def __init__(self, trade_id: int):
        super().__init__(f"Trade {trade_id} not found in MT5 - phantom",
                        f"DB_ID_{trade_id}", "NOT_IN_MT5")

class OrphanPositionError(DataIntegrityError):
    """Position exists in MT5 but not in DB"""
    def __init__(self, position_id: int):
        super().__init__(f"Position {position_id} not in database - orphan",
                        "NOT_IN_DB", f"MT5_POS_{position_id}")

class PnLMismatchError(DataIntegrityError):
    """PnL differs between DB and MT5"""
    def __init__(self, trade_id: int, db_pnl: float, mt5_pnl: float):
        super().__init__(f"PnL mismatch for trade {trade_id}: DB=${db_pnl:.2f} vs MT5=${mt5_pnl:.2f}",
                        db_pnl, mt5_pnl)

class TimestampError(DataIntegrityError):
    """Exit time before entry time"""
    def __init__(self, trade_id: int, entry: str, exit: str):
        super().__init__(f"Timestamp error: exit {exit} before entry {entry}",
                        entry, exit)

# ============================================================================
# ENFORCEMENT HELPERS
# ============================================================================

def require_regime(regime: Optional[str], pair: str) -> str:
    """Regime is required - raise if missing"""
    if not regime or regime == 'UNKNOWN':
        raise MissingRegimeError(pair)
    return regime

def require_confidence(confidence: Optional[float], pair: str, min_conf: float = 0.5) -> float:
    """Confidence is required and must meet minimum"""
    if confidence is None:
        raise MissingConfidenceError(pair, confidence)
    if confidence < min_conf:
        raise TradeRejectionError(
            f"Confidence {confidence:.2f} below minimum {min_conf}",
            {"pair": pair, "confidence": confidence, "min": min_conf}
        )
    if confidence > 1.0 or confidence < 0:
        raise MissingConfidenceError(pair, confidence)
    return confidence

def require_metadata(field_name: str, value: Any, pair: str) -> Any:
    """Metadata field is required - raise if missing"""
    if value is None or value == '' or value == 'UNKNOWN':
        raise MissingMetadataError(field_name, pair)
    return value

def require_not_stale(price: float, stale_value: float = 1.15123, pair: str = "") -> float:
    """Price must not match known stale cache value"""
    if abs(price - stale_value) < 0.00001:
        raise StaleSignalError(pair, price)
    return price

def require_valid_lot(volume: float, min_vol: float, max_vol: float) -> float:
    """Volume must be within broker limits"""
    if volume < min_vol or volume > max_vol:
        raise LotSizeError(volume, min_vol, max_vol)
    return volume

def require_risk_ok(actual_risk: float, max_risk: float, reason: str = "") -> float:
    """Actual risk must not exceed maximum"""
    if actual_risk > max_risk:
        raise RiskViolationError(reason, actual_risk, max_risk)
    return actual_risk

def require_entry_after_exit(entry_time: str, exit_time: str, trade_id: int) -> bool:
    """Exit must be after entry"""
    if exit_time < entry_time:
        raise TimestampError(trade_id, entry_time, exit_time)
    return True
