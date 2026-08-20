"""Validation Lock - Enforces safe trading limits until proven otherwise.
Per advisor: Do NOT increase risk. Stay in VALIDATION MODE. 0.01 lot maximum.
"""
from dataclasses import dataclass
from enum import Enum

class ValidationState(str, Enum):
    LOCKED = "LOCKED"       # Hard limits enforced
    REVIEW = "REVIEW"       # Under panel review
    UNLOCKED = "UNLOCKED"   # Production approval granted

@dataclass(frozen=True)
class ValidationLimits:
    """Immutable validation limits - CANNOT be modified at runtime"""
    max_volume: float = 0.01          # Absolute maximum lot size
    max_risk_pct: float = 0.0005      # 0.05% risk per trade
    max_daily_trades: int = 5         # Daily trade cap
    max_daily_loss_pct: float = 0.05  # 5% max daily loss
    max_open_positions: int = 3       # Portfolio cap
    min_qualified_trades_to_review: int = 10    # Need 10 before any review
    min_trades_for_strategy_review: int = 50    # Need 50 before strategy analysis
    min_trades_for_statistical_validation: int = 100  # Need 100 for stats
    min_trades_for_production: int = 300   # Need 300 for production consideration
    signal_max_age_seconds: int = 120   # Signal freshness window
    max_entry_deviation_pips: float = 5.0  # Maximum acceptable slippage

VALIDATION_LIMITS = ValidationLimits()

def assert_validation_safe(volume: float, risk_pct: float, trades_today: int) -> bool:
    """
    HARD CHECK: Ensure we stay within validation limits.
    Called before EVERY order. Returns False if any limit exceeded.
    """
    if volume > VALIDATION_LIMITS.max_volume:
        print(f"[VALIDATION LOCK] REJECT: Volume {volume} > max {VALIDATION_LIMITS.max_volume}")
        return False
    if risk_pct > VALIDATION_LIMITS.max_risk_pct:
        print(f"[VALIDATION LOCK] REJECT: Risk {risk_pct} > max {VALIDATION_LIMITS.max_risk_pct}")
        return False
    if trades_today >= VALIDATION_LIMITS.max_daily_trades:
        print(f"[VALIDATION LOCK] REJECT: Daily limit {trades_today}/{VALIDATION_LIMITS.max_daily_trades}")
        return False
    return True

def get_validation_status(qualified_trades: int) -> dict:
    """Get validation progress based on qualified trade count"""
    status = {
        "state": ValidationState.LOCKED.value,
        "qualified_trades": qualified_trades,
        "max_volume": VALIDATION_LIMITS.max_volume,
        "max_risk_pct": VALIDATION_LIMITS.max_risk_pct,
        "next_review_at": VALIDATION_LIMITS.min_qualified_trades_to_review,
        "strategy_review_at": VALIDATION_LIMITS.min_trades_for_strategy_review,
        "statistical_validation_at": VALIDATION_LIMITS.min_trades_for_statistical_validation,
        "production_consideration_at": VALIDATION_LIMITS.min_trades_for_production,
    }
    
    if qualified_trades >= VALIDATION_LIMITS.min_qualified_trades_to_review:
        status["state"] = ValidationState.REVIEW.value
    
    return status
