"""P0: Monetary Risk Gate - Enforces risk BUDGET, not just lot size.
Replaces the pattern: "0.01 lots is safe" -> "actual_risk <= allowed_risk"
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class MonetaryRiskCheck:
    """The FINAL check before MT5 - actual dollar risk vs budget"""
    equity: float
    risk_pct: float              # e.g., 0.0005 for 0.05%
    entry_price: float
    stop_loss: float
    volume: float
    pip_value_per_lot: float     # $10 for EURUSD standard lot
    
    @property
    def risk_budget(self) -> float:
        """Maximum dollar amount we're allowed to risk"""
        return self.equity * self.risk_pct
    
    @property
    def stop_distance_pips(self) -> float:
        """Stop distance in pips"""
        return abs(self.entry_price - self.stop_loss) / 0.0001
    
    @property
    def actual_risk(self) -> float:
        """Actual dollar risk at stop loss"""
        return self.stop_distance_pips * self.pip_value_per_lot * self.volume
    
    @property
    def is_safe(self) -> bool:
        """HARD INVARIANT: actual_risk <= risk_budget"""
        return self.actual_risk <= self.risk_budget * 1.01  # 1% tolerance
    
    @property
    def risk_ratio(self) -> float:
        """How many times the budget we're risking"""
        return self.actual_risk / self.risk_budget if self.risk_budget > 0 else float('inf')
    
    def summary(self) -> str:
        lines = [
            f"MONETARY RISK CHECK",
            f"  Equity: ${self.equity:.2f}",
            f"  Risk Budget ({self.risk_pct*100:.2f}%): ${self.risk_budget:.4f}",
            f"  Stop Distance: {self.stop_distance_pips:.1f} pips",
            f"  Volume: {self.volume} lots",
            f"  Pip Value/Lot: ${self.pip_value_per_lot:.2f}",
            f"  Actual Risk at SL: ${self.actual_risk:.2f}",
        ]
        if self.is_safe:
            lines.append(f"  STATUS: SAFE (${self.actual_risk:.2f} <= ${self.risk_budget:.4f})")
        else:
            lines.append(f"  STATUS: REJECTED - Risk ${self.actual_risk:.2f} exceeds budget ${self.risk_budget:.4f} by {self.risk_ratio:.1f}x")
        return "\n".join(lines)


def enforce_monetary_risk(equity: float, risk_pct: float, entry: float,
                          sl: float, volume: float, pip_value: float = 10.0) -> MonetaryRiskCheck:
    """
    P0: THE final check before mt5.order_send().
    
    Returns MonetaryRiskCheck. If check.is_safe is False, DO NOT SEND ORDER.
    """
    check = MonetaryRiskCheck(equity, risk_pct, entry, sl, volume, pip_value)
    if not check.is_safe:
        raise RiskBudgetExceededError(check)
    return check


class RiskBudgetExceededError(Exception):
    def __init__(self, check: MonetaryRiskCheck):
        self.check = check
        super().__init__(
            f"RISK BUDGET EXCEEDED: ${check.actual_risk:.2f} > ${check.risk_budget:.4f} "
            f"({check.risk_ratio:.1f}x budget). ORDER BLOCKED."
        )


# Test with ID 163's actual trade
if __name__ == "__main__":
    # Live_Micro: $19.06, 0.05% risk, EURUSD, 0.01 lot, 3.3 pip SL
    check = MonetaryRiskCheck(
        equity=19.06,
        risk_pct=0.0005,
        entry_price=1.15542,
        stop_loss=1.15575,  # ~3.3 pip SL (actual trade)
        volume=0.01,
        pip_value_per_lot=10.0,
    )
    print(check.summary())
    print(f"\n  Lesson: Even 0.01 lots can exceed 0.05% budget on $19 account")
    print(f"  Minimum equity for 0.01 lot, 17.6 pip SL, 0.05% risk: ${0.01 * 10 * 17.6 / 0.0005:,.0f}")
