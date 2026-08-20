"""Explicit, Deterministic Position Sizing - No hidden behavior.
All calculations use clearly defined inputs with explicit types.
"""
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

class AccountCurrency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

@dataclass(frozen=True)
class SymbolSpecs:
    """Immutable broker symbol specifications - THE source of truth for calculations"""
    symbol: str
    tick_value: float       # Value of one tick in account currency
    tick_size: float        # Size of one tick in price units
    point: float            # Point size (e.g., 0.00001 for 5-digit EURUSD)
    contract_size: float    # Contract size (e.g., 100000 for standard forex lot)
    volume_min: float       # Minimum volume (e.g., 0.01)
    volume_max: float       # Maximum volume (e.g., 100.0)
    volume_step: float      # Volume step (e.g., 0.01)
    digits: int             # Price decimal places (e.g., 5)
    stops_level: int        # Minimum stop distance in points (0 = no minimum)
    
    @property
    def pip_value_per_lot(self) -> float:
        """Value of 1 pip for 1 standard lot"""
        return (self.tick_value / self.tick_size) * (self.point * 10)
    
    @property
    def min_notional(self) -> float:
        """Minimum notional value at current price"""
        return self.contract_size * self.volume_min

@dataclass(frozen=True)
class RiskParams:
    """Immutable risk parameters for a trade decision"""
    account_balance: float          # Current account balance
    account_currency: AccountCurrency
    risk_pct: float                 # Risk percentage (e.g., 0.0005 for 0.05%)
    max_daily_trades: int           # Maximum trades per day
    max_portfolio_risk_pct: float   # Maximum total portfolio risk
    
    @property
    def risk_amount(self) -> float:
        """Maximum dollar amount to risk on this trade"""
        return self.account_balance * self.risk_pct
    
    def validate(self) -> list:
        """Validate risk parameters - returns list of issues"""
        issues = []
        if self.risk_pct <= 0 or self.risk_pct > 0.05:
            issues.append(f"risk_pct {self.risk_pct} out of range (0-5%)")
        if self.account_balance <= 0:
            issues.append(f"account_balance {self.account_balance} invalid")
        if self.max_daily_trades < 1:
            issues.append(f"max_daily_trades {self.max_daily_trades} too low")
        return issues

@dataclass(frozen=True)
class PositionSizeResult:
    """Deterministic position sizing result - all values explicit"""
    # Inputs
    risk_params: RiskParams
    symbol_specs: SymbolSpecs
    entry_price: float
    stop_loss_price: float
    
    # Calculated
    stop_distance_pips: float       # Stop distance in pips
    stop_distance_points: float     # Stop distance in points
    risk_per_lot: float             # Dollar risk per standard lot at this stop distance
    theoretical_lot: float          # Ideal lot size based on risk
    broker_valid_lot: float         # Lot size adjusted to broker volume step
    is_tradable: bool               # Whether broker minimum lot <= theoretical lot
    rejection_reason: Optional[str] # Why it was rejected, if not tradable
    
    # Risk exposure
    actual_risk_amount: float       # Actual dollar risk at broker_valid_lot
    risk_to_balance_pct: float      # Actual risk as % of balance
    notional_value: float           # Notional value of position
    
    def summary(self) -> str:
        """Human-readable summary of the position sizing decision"""
        lines = [
            f"Position Size Calculation",
            f"  Symbol: {self.symbol_specs.symbol}",
            f"  Entry: {self.entry_price:.{self.symbol_specs.digits}f}",
            f"  Stop Loss: {self.stop_loss_price:.{self.symbol_specs.digits}f}",
            f"  Stop Distance: {self.stop_distance_pips:.1f} pips",
            f"  Risk per Lot: ${self.risk_per_lot:.2f}",
            f"  Risk Budget: ${self.risk_params.risk_amount:.4f}",
            f"  Theoretical Lot: {self.theoretical_lot:.6f}",
            f"  Broker Min Lot: {self.symbol_specs.volume_min}",
            f"  Broker Valid Lot: {self.broker_valid_lot:.2f}",
        ]
        if self.is_tradable:
            lines.append(f"  STATUS: TRADABLE")
            lines.append(f"  Actual Risk: ${self.actual_risk_amount:.2f} ({self.risk_to_balance_pct:.2f}% of balance)")
            lines.append(f"  Notional: ${self.notional_value:,.0f}")
        else:
            lines.append(f"  STATUS: REJECTED - {self.rejection_reason}")
        return "\n".join(lines)


def calculate_position_size(
    risk_params: RiskParams,
    symbol_specs: SymbolSpecs,
    entry_price: float,
    stop_loss_price: float,
) -> PositionSizeResult:
    """
    Deterministic position sizing with NO hidden behavior.
    
    All inputs are explicit, typed, and immutable.
    The result is fully deterministic given the same inputs.
    
    Args:
        risk_params: Account risk parameters
        symbol_specs: Broker symbol specifications
        entry_price: Planned entry price
        stop_loss_price: Stop loss price
    
    Returns:
        PositionSizeResult with all calculated values
    """
    # 1. Calculate stop distance
    stop_distance = abs(entry_price - stop_loss_price)
    stop_distance_points = stop_distance / symbol_specs.point
    stop_distance_pips = stop_distance / (symbol_specs.point * 10)
    
    # 2. Calculate risk per standard lot at this stop distance
    risk_per_lot = stop_distance_pips * symbol_specs.pip_value_per_lot
    
    # 3. Calculate theoretical lot size
    if risk_per_lot > 0:
        theoretical_lot = risk_params.risk_amount / risk_per_lot
    else:
        theoretical_lot = 0.0
    
    # 4. Adjust to broker volume step
    broker_valid_lot = max(
        symbol_specs.volume_min,
        min(
            symbol_specs.volume_max,
            round(theoretical_lot / symbol_specs.volume_step) * symbol_specs.volume_step
        )
    )
    
    # 5. Check tradability
    if theoretical_lot <= 0:
        is_tradable = False
        rejection_reason = "Zero or negative stop distance"
    elif theoretical_lot < symbol_specs.volume_min:
        is_tradable = False
        rejection_reason = (
            f"Minimum broker lot ({symbol_specs.volume_min}) exceeds "
            f"risk budget. Need ${risk_per_lot * symbol_specs.volume_min:.2f} "
            f"risk but budget is ${risk_params.risk_amount:.4f}"
        )
    elif broker_valid_lot > symbol_specs.volume_max:
        is_tradable = False
        rejection_reason = f"Required lot {broker_valid_lot} exceeds max {symbol_specs.volume_max}"
    else:
        is_tradable = True
        rejection_reason = None
    
    # 6. Calculate actual risk exposure
    actual_risk_amount = risk_per_lot * broker_valid_lot
    risk_to_balance_pct = (actual_risk_amount / risk_params.account_balance * 100) if risk_params.account_balance > 0 else 0
    notional_value = symbol_specs.contract_size * broker_valid_lot * entry_price
    
    return PositionSizeResult(
        risk_params=risk_params,
        symbol_specs=symbol_specs,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        stop_distance_pips=round(stop_distance_pips, 1),
        stop_distance_points=round(stop_distance_points, 1),
        risk_per_lot=round(risk_per_lot, 2),
        theoretical_lot=round(theoretical_lot, 6),
        broker_valid_lot=round(broker_valid_lot, 2),
        is_tradable=is_tradable,
        rejection_reason=rejection_reason,
        actual_risk_amount=round(actual_risk_amount, 2),
        risk_to_balance_pct=round(risk_to_balance_pct, 2),
        notional_value=round(notional_value, 0),
    )


# ============================================================================
# STANDARD SYMBOL SPECS (Exness MT5)
# ============================================================================

EURUSD_SPECS = SymbolSpecs(
    symbol="EURUSD",
    tick_value=1.0,         # $1 per tick for 1 lot
    tick_size=0.00001,      # 0.00001 tick size (5-digit)
    point=0.00001,          # 0.00001 point
    contract_size=100000,   # 100,000 base currency per lot
    volume_min=0.01,        # 0.01 lots minimum
    volume_max=100.0,       # 100 lots maximum
    volume_step=0.01,       # 0.01 lot increments
    digits=5,               # 5 decimal places
    stops_level=0,          # No minimum stop distance
)

GBPUSD_SPECS = SymbolSpecs(
    symbol="GBPUSD",
    tick_value=1.0,
    tick_size=0.00001,
    point=0.00001,
    contract_size=100000,
    volume_min=0.01,
    volume_max=100.0,
    volume_step=0.01,
    digits=5,
    stops_level=0,
)

USDJPY_SPECS = SymbolSpecs(
    symbol="USDJPY",
    tick_value=1.0,
    tick_size=0.001,        # 0.001 tick size (3-digit for JPY)
    point=0.001,
    contract_size=100000,
    volume_min=0.01,
    volume_max=100.0,
    volume_step=0.01,
    digits=3,
    stops_level=0,
)
