"""FOREX-AI-APP Domain Layer - Type-safe trading domain models."""
from packages.domain.models import (
    TradeLifecycle, Signal, Position, Deal, TradeIntent,
    OrderRequest, OrderResult, TradeResult, SignalDirection,
    TradeMode, Environment, create_trade_from_signal,
)
from packages.domain.invariants import (
    TradeInvariants, InvariantViolation, DataIntegrityError,
    enforce_invariants,
)
from packages.domain.errors import (
    ForexError, TradeRejectionError, MissingRegimeError,
    StaleSignalError, RiskViolationError, LotSizeError,
    require_regime, require_confidence, require_metadata,
    require_not_stale, require_valid_lot, require_risk_ok,
)
