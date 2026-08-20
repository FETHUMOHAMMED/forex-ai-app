"""Authoritative Domain Model - Single source of truth for all trading entities"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum

# ============================================================================
# ENUMS
# ============================================================================

class TradeResult(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    OPEN = "OPEN"

class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class TradeMode(str, Enum):
    VALIDATION = "VALIDATION"
    PRODUCTION = "PRODUCTION"
    BACKTEST = "BACKTEST"

class Environment(str, Enum):
    LIVE_MICRO = "LIVE_MICRO"
    LIVE_MICRO_VALIDATION = "LIVE_MICRO_VALIDATION"
    DEMO = "DEMO"

class DealType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class DealEntry(str, Enum):
    IN = "IN"
    OUT = "OUT"

# ============================================================================
# DOMAIN OBJECTS
# ============================================================================

@dataclass
class MarketData:
    """Immutable market snapshot at a point in time"""
    symbol: str
    bid: float
    ask: float
    spread: float
    timestamp_utc: datetime
    timeframe: str = "M1"

@dataclass  
class Signal:
    """AI-generated trading signal - immutable at creation"""
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
    dealer_pressure: str
    liquidity_state: str
    continuation_prob: float
    timestamp_utc: datetime
    
    def __post_init__(self):
        assert 0 <= self.confidence <= 1, f"Confidence {self.confidence} out of range"
        assert self.entry_price > 0, f"Entry price {self.entry_price} invalid"
        assert self.stop_loss > 0, f"SL {self.stop_loss} invalid"
        assert self.take_profit > 0, f"TP {self.take_profit} invalid"

@dataclass
class TradeIntent:
    """Decision to place a trade, before execution"""
    signal: Signal
    account_id: int
    account_name: str
    environment: Environment
    trade_mode: TradeMode
    strategy_version: str
    risk_pct: float
    calculated_lot: float
    broker_min_lot: float
    final_lot: float
    
    @property
    def is_rejected_due_to_lot_size(self) -> bool:
        return self.final_lot < self.broker_min_lot

@dataclass
class OrderRequest:
    """MT5 order request payload"""
    symbol: str
    order_type: int  # mt5.ORDER_TYPE_BUY/SELL
    volume: float
    price: float
    sl: float
    tp: float
    deviation: int
    magic: int
    comment: str

@dataclass  
class OrderResult:
    """MT5 order_send response"""
    retcode: int
    order_ticket: Optional[int]
    deal_ticket: Optional[int]
    comment: str
    timestamp_utc: datetime

@dataclass
class Position:
    """MT5 position - immutable snapshot"""
    position_id: int
    symbol: str
    direction: SignalDirection
    volume: float
    open_price: float
    open_time_utc: datetime
    sl: float
    tp: float
    current_price: Optional[float] = None
    current_profit: Optional[float] = None

@dataclass
class Deal:
    """MT5 deal (entry or exit)"""
    deal_id: int
    position_id: int
    order_id: int
    deal_type: DealType
    deal_entry: DealEntry
    volume: float
    price: float
    profit: float
    commission: float
    swap: float
    time_utc: datetime
    reason: int

@dataclass
class TradeLifecycle:
    """Complete trade from signal to close - THE authoritative record"""
    # Database ID
    db_id: Optional[int] = None
    
    # Signal (immutable snapshot at creation)
    signal: Optional[Signal] = None
    
    # Intent & Risk
    intent: Optional[TradeIntent] = None
    
    # Execution - MT5 verified
    order_result: Optional[OrderResult] = None
    position: Optional[Position] = None
    entry_deal: Optional[Deal] = None
    exit_deal: Optional[Deal] = None
    
    # Actual execution prices (from MT5, NOT signal)
    actual_entry: Optional[float] = None
    actual_sl: Optional[float] = None
    actual_tp: Optional[float] = None
    actual_exit: Optional[float] = None
    
    # Financial result (from MT5 deals)
    realized_pnl: Optional[float] = None
    commission: float = 0.0
    swap: float = 0.0
    
    # State
    result: Optional[TradeResult] = None
    opened_at_utc: Optional[datetime] = None
    closed_at_utc: Optional[datetime] = None
    
    # Metadata
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    environment: Optional[Environment] = None
    trade_mode: Optional[TradeMode] = None
    strategy_version: Optional[str] = None
    
    @property
    def is_mt5_verified(self) -> bool:
        """Trade was actually executed in MT5"""
        return self.position is not None and self.position.position_id is not None
    
    @property
    def is_complete(self) -> bool:
        """Trade has both entry and exit"""
        return self.entry_deal is not None and self.exit_deal is not None
    
    @property
    def net_pnl(self) -> float:
        """Realized PnL including all costs"""
        if self.realized_pnl is None:
            return 0.0
        return self.realized_pnl + self.commission + self.swap
    
    @property
    def entry_slippage_pips(self) -> Optional[float]:
        """Difference between planned and actual entry in pips"""
        if self.signal and self.actual_entry:
            return abs(self.actual_entry - self.signal.entry_price) * 10000
        return None
    
    def validate(self) -> List[str]:
        """Validate data integrity - returns list of issues"""
        issues = []
        if self.closed_at_utc and self.opened_at_utc:
            if self.closed_at_utc < self.opened_at_utc:
                issues.append(f"CLOSE_BEFORE_OPEN: {self.closed_at_utc} < {self.opened_at_utc}")
        if self.is_complete and self.realized_pnl is None:
            issues.append("MISSING_PNL")
        if not self.position:
            issues.append("NO_MT5_POSITION")
        if self.signal and self.signal.entry_price == self.actual_entry == 1.15123:
            issues.append("STALE_SIGNAL_PRICE")
        return issues

@dataclass
class AccountSnapshot:
    """Point-in-time account state"""
    account_id: int
    account_name: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    timestamp_utc: datetime

# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_trade_from_signal(signal: Signal, account_id: int, account_name: str,
                              environment: Environment, trade_mode: TradeMode,
                              strategy_version: str) -> TradeLifecycle:
    """Create a new trade lifecycle from a signal"""
    return TradeLifecycle(
        signal=signal,
        account_id=account_id,
        account_name=account_name,
        environment=environment,
        trade_mode=trade_mode,
        strategy_version=strategy_version,
        opened_at_utc=datetime.now(timezone.utc)
    )
