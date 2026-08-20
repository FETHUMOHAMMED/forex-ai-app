"""Order Boundary Risk Enforcement - THE final gate before MT5.
Every order MUST pass this boundary. No exceptions.

Signal -> Trade Plan -> Risk Engine -> Symbol Specs -> Risk Calc -> Volume -> ASSERTION -> ORDER
                                                                                          |
                                                                                    REJECTED if fail
"""
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class RiskGateResult(str, Enum):
    APPROVED = "APPROVED"
    REJECTED_LOT_TOO_LARGE = "REJECTED_LOT_TOO_LARGE"
    REJECTED_LOT_TOO_SMALL = "REJECTED_LOT_TOO_SMALL"
    REJECTED_RISK_EXCEEDS_BUDGET = "REJECTED_RISK_EXCEEDS_BUDGET"
    REJECTED_DAILY_LIMIT = "REJECTED_DAILY_LIMIT"
    REJECTED_MAX_DRAWDOWN = "REJECTED_MAX_DRAWDOWN"
    REJECTED_PORTFOLIO_RISK = "REJECTED_PORTFOLIO_RISK"
    REJECTED_CORRELATION = "REJECTED_CORRELATION"
    REJECTED_MARGIN = "REJECTED_MARGIN"
    REJECTED_SYMBOL_SPECS = "REJECTED_SYMBOL_SPECS"

@dataclass(frozen=True)
class RiskGate:
    """Immutable risk gate result - the final word on whether an order proceeds"""
    result: RiskGateResult
    reason: str
    actual_risk_amount: float
    risk_pct_of_balance: float
    volume: float
    is_approved: bool
    
    def assert_or_raise(self):
        """Call this before mt5.order_send(). Raises if rejected."""
        if not self.is_approved:
            raise RiskGateRejectedError(self)
        return self

class RiskGateRejectedError(Exception):
    def __init__(self, gate: RiskGate):
        self.gate = gate
        super().__init__(f"[RISK GATE] {gate.result.value}: {gate.reason}")


# ============================================================================
# THE RISK GATE - Called immediately before EVERY mt5.order_send()
# ============================================================================

def enforce_order_boundary(
    # Account state (from MT5 - authoritative)
    account_balance: float,
    account_equity: float,
    account_free_margin: float,
    
    # Daily state
    trades_today: int,
    max_daily_trades: int,
    daily_pnl: float,
    max_daily_loss_pct: float,
    
    # Portfolio state
    open_positions_count: int,
    max_open_positions: int,
    total_portfolio_risk_pct: float,
    max_portfolio_risk_pct: float,
    
    # Trade parameters
    symbol: str,
    volume: float,
    entry_price: float,
    stop_loss: float,
    
    # Symbol specs (from MT5 - authoritative)
    symbol_volume_min: float,
    symbol_volume_max: float,
    symbol_volume_step: float,
    symbol_tick_value: float,
    symbol_tick_size: float,
    symbol_point: float,
    symbol_contract_size: float,
    
    # Risk budget
    max_risk_pct_per_trade: float,
    
) -> RiskGate:
    """
    THE FINAL GATE before mt5.order_send().
    
    Returns RiskGate. Call .assert_or_raise() to block rejected orders.
    This function MUST be called immediately before every order.
    No order reaches MT5 without passing this gate.
    """
    
    # 1. Daily limit check
    if trades_today >= max_daily_trades:
        return RiskGate(
            result=RiskGateResult.REJECTED_DAILY_LIMIT,
            reason=f"Daily limit reached: {trades_today}/{max_daily_trades}",
            actual_risk_amount=0, risk_pct_of_balance=0,
            volume=volume, is_approved=False
        )
    
    # 2. Daily drawdown check
    if daily_pnl < 0:
        daily_loss_pct = abs(daily_pnl) / account_balance
        if daily_loss_pct > max_daily_loss_pct:
            return RiskGate(
                result=RiskGateResult.REJECTED_MAX_DRAWDOWN,
                reason=f"Daily loss {daily_loss_pct*100:.1f}% exceeds max {max_daily_loss_pct*100:.1f}%",
                actual_risk_amount=0, risk_pct_of_balance=daily_loss_pct*100,
                volume=volume, is_approved=False
            )
    
    # 3. Volume validation against symbol specs
    if volume < symbol_volume_min:
        return RiskGate(
            result=RiskGateResult.REJECTED_LOT_TOO_SMALL,
            reason=f"Volume {volume} < symbol min {symbol_volume_min}",
            actual_risk_amount=0, risk_pct_of_balance=0,
            volume=volume, is_approved=False
        )
    
    if volume > symbol_volume_max:
        return RiskGate(
            result=RiskGateResult.REJECTED_LOT_TOO_LARGE,
            reason=f"Volume {volume} > symbol max {symbol_volume_max}",
            actual_risk_amount=0, risk_pct_of_balance=0,
            volume=volume, is_approved=False
        )
    
    # 4. Calculate ACTUAL monetary risk (from MT5 symbol specs - authoritative)
    stop_distance_points = abs(entry_price - stop_loss) / symbol_point
    pip_value_per_lot = (symbol_tick_value / symbol_tick_size) * symbol_point * 10
    stop_distance_pips = stop_distance_points * symbol_point * 10
    pip_value_per_lot = (symbol_tick_value / symbol_tick_size) * symbol_point * 10
    actual_risk_amount = stop_distance_pips * pip_value_per_lot * volume
    
    # 5. Risk budget check
    max_risk_amount = account_balance * max_risk_pct_per_trade
    risk_pct = (actual_risk_amount / account_balance * 100) if account_balance > 0 else 0
    
    if actual_risk_amount > max_risk_amount:
        return RiskGate(
            result=RiskGateResult.REJECTED_RISK_EXCEEDS_BUDGET,
            reason=f"Risk ${actual_risk_amount:.2f} ({risk_pct:.1f}%) exceeds budget ${max_risk_amount:.2f} ({max_risk_pct_per_trade*100:.2f}%)",
            actual_risk_amount=actual_risk_amount, risk_pct_of_balance=risk_pct,
            volume=volume, is_approved=False
        )
    
    # 6. Margin check
    notional = symbol_contract_size * volume * entry_price
    margin_required = notional * 0.01  # Approximate 1% margin
    if margin_required > account_free_margin:
        return RiskGate(
            result=RiskGateResult.REJECTED_MARGIN,
            reason=f"Margin ${margin_required:.0f} > free margin ${account_free_margin:.0f}",
            actual_risk_amount=actual_risk_amount, risk_pct_of_balance=risk_pct,
            volume=volume, is_approved=False
        )
    
    # 7. Portfolio risk check
    if total_portfolio_risk_pct + risk_pct / 100 > max_portfolio_risk_pct:
        return RiskGate(
            result=RiskGateResult.REJECTED_PORTFOLIO_RISK,
            reason=f"Portfolio risk {(total_portfolio_risk_pct + risk_pct/100)*100:.1f}% exceeds max {max_portfolio_risk_pct*100:.1f}%",
            actual_risk_amount=actual_risk_amount, risk_pct_of_balance=risk_pct,
            volume=volume, is_approved=False
        )
    
    # 8. Open positions check
    if open_positions_count >= max_open_positions:
        return RiskGate(
            result=RiskGateResult.REJECTED_PORTFOLIO_RISK,
            reason=f"Max positions reached: {open_positions_count}/{max_open_positions}",
            actual_risk_amount=actual_risk_amount, risk_pct_of_balance=risk_pct,
            volume=volume, is_approved=False
        )
    
    # ALL CHECKS PASSED
    return RiskGate(
        result=RiskGateResult.APPROVED,
        reason="All risk checks passed",
        actual_risk_amount=actual_risk_amount,
        risk_pct_of_balance=risk_pct,
        volume=volume,
        is_approved=True
    )


# ============================================================================
# CONVENIENCE: Fetch symbol specs from MT5
# ============================================================================

def get_mt5_symbol_specs(symbol: str) -> dict:
    """Fetch authoritative symbol specs from MT5"""
    import MetaTrader5 as mt5
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"Symbol {symbol} not available in MT5")
    return {
        "symbol_volume_min": info.volume_min,
        "symbol_volume_max": info.volume_max,
        "symbol_volume_step": info.volume_step,
        "symbol_tick_value": info.trade_tick_value,
        "symbol_tick_size": info.trade_tick_size,
        "symbol_point": info.point,
        "symbol_contract_size": info.trade_contract_size,
    }


def get_mt5_account_state() -> dict:
    """Fetch authoritative account state from MT5"""
    import MetaTrader5 as mt5
    info = mt5.account_info()
    if info is None:
        raise ValueError("MT5 account not connected")
    return {
        "account_balance": info.balance,
        "account_equity": info.equity,
        "account_free_margin": info.margin_free,
    }
