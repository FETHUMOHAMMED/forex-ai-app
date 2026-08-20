"""FastAPI Request/Response models - Explicit trading state transitions.
Each endpoint represents ONE state transition, not a hidden chain.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ============================================================================
# ENUMS
# ============================================================================

class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class TradeResult(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    OPEN = "OPEN"

class RiskDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED_LOT_SIZE = "REJECTED_LOT_SIZE"
    REJECTED_RISK_BUDGET = "REJECTED_RISK_BUDGET"
    REJECTED_DAILY_LIMIT = "REJECTED_DAILY_LIMIT"
    REJECTED_PORTFOLIO_RISK = "REJECTED_PORTFOLIO_RISK"

class ReconciliationStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    PHANTOM = "PHANTOM"       # In DB but not MT5
    ORPHAN = "ORPHAN"          # In MT5 but not DB
    PENDING = "PENDING"

# ============================================================================
# REQUEST MODELS - One per state transition
# ============================================================================

class SignalRequest(BaseModel):
    """POST /signals - Request AI signal generation"""
    symbol: str = Field(..., example="EURUSD")
    timeframe: str = Field(default="H1", example="H1")

class TradeIntentRequest(BaseModel):
    """POST /trade-intents - Propose a trade (BEFORE execution)"""
    signal_id: str
    symbol: str
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float = Field(..., ge=0, le=1)
    account_id: int
    risk_pct: float = Field(default=0.0005, description="0.05% risk")

class RiskCheckRequest(BaseModel):
    """POST /risk-check - Validate risk before order"""
    trade_intent_id: str
    account_balance: float
    symbol: str
    entry_price: float
    stop_loss: float
    volume: float

class OrderRequest(BaseModel):
    """POST /orders - Place an MT5 order (AFTER risk check)"""
    risk_check_id: str
    symbol: str
    direction: SignalDirection
    volume: float
    entry_price: float
    stop_loss: float
    take_profit: float
    deviation: int = Field(default=30)
    magic: int = Field(default=234000)

# ============================================================================
# RESPONSE MODELS - Explicit results
# ============================================================================

class SignalResponse(BaseModel):
    """GET /signals response"""
    signal_id: str
    symbol: str
    direction: SignalDirection
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    regime: str
    institutional_bias: str
    institutional_score: float
    timestamp_utc: datetime

class TradeIntentResponse(BaseModel):
    """POST /trade-intents response"""
    intent_id: str
    signal_id: str
    calculated_lot: float
    broker_min_lot: float
    is_tradable: bool
    risk_amount: float
    rejection_reason: Optional[str] = None

class RiskCheckResponse(BaseModel):
    """POST /risk-check response"""
    check_id: str
    decision: RiskDecision
    actual_risk_amount: float
    risk_to_balance_pct: float
    is_approved: bool
    detail: str

class OrderResponse(BaseModel):
    """POST /orders response"""
    order_id: str
    mt5_order_ticket: Optional[int] = None
    mt5_position_id: Optional[int] = None
    mt5_deal_ticket: Optional[int] = None
    retcode: int
    comment: str
    is_filled: bool
    timestamp_utc: datetime

class PositionResponse(BaseModel):
    """GET /positions response"""
    position_id: int
    symbol: str
    direction: SignalDirection
    volume: float
    open_price: float
    current_price: Optional[float] = None
    profit: Optional[float] = None
    sl: float
    tp: float
    open_time_utc: datetime

class AccountResponse(BaseModel):
    """GET /accounts response"""
    account_id: int
    account_name: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    server: str
    timestamp_utc: datetime

class ReconciliationResponse(BaseModel):
    """GET /reconciliation - Compare DB vs MT5"""
    db_trade_id: int
    mt5_position_id: Optional[int]
    status: ReconciliationStatus
    db_entry: Optional[float] = None
    mt5_entry: Optional[float] = None
    db_exit: Optional[float] = None
    mt5_exit: Optional[float] = None
    db_pnl: Optional[float] = None
    mt5_pnl: Optional[float] = None
    pnl_match: bool = False
    issues: List[str] = Field(default_factory=list)

class HealthResponse(BaseModel):
    """GET /health response"""
    status: str  # "healthy", "degraded", "down"
    services: dict
    mt5_connected: bool
    database_connected: bool
    last_heartbeat_utc: Optional[datetime] = None
    uptime_seconds: float

# ============================================================================
# STATE MACHINE - Enforced transitions
# ============================================================================

class TradeState(str, Enum):
    """Explicit trade state machine"""
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    INTENT_CREATED = "INTENT_CREATED"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    ORDER_SENT = "ORDER_SENT"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    POSITION_OPEN = "POSITION_OPEN"
    POSITION_CLOSED = "POSITION_CLOSED"
    RECONCILED = "RECONCILED"

# Valid transitions
VALID_TRANSITIONS = {
    TradeState.SIGNAL_GENERATED: [TradeState.INTENT_CREATED],
    TradeState.INTENT_CREATED: [TradeState.RISK_APPROVED, TradeState.RISK_REJECTED],
    TradeState.RISK_APPROVED: [TradeState.ORDER_SENT],
    TradeState.ORDER_SENT: [TradeState.ORDER_FILLED, TradeState.ORDER_REJECTED],
    TradeState.ORDER_FILLED: [TradeState.POSITION_OPEN],
    TradeState.POSITION_OPEN: [TradeState.POSITION_CLOSED],
    TradeState.POSITION_CLOSED: [TradeState.RECONCILED],
    TradeState.RECONCILED: [],  # Terminal state
}

def is_valid_transition(from_state: TradeState, to_state: TradeState) -> bool:
    """Enforce explicit state transitions - no skipping steps"""
    return to_state in VALID_TRANSITIONS.get(from_state, [])
