"""Portfolio Engine - Multi-currency exposure and correlation management."""
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

@dataclass
class CurrencyExposure:
    """Exposure to one currency."""
    currency: str
    net_exposure: float  # Long - Short (in base currency units)
    long_exposure: float
    short_exposure: float

@dataclass
class PortfolioRisk:
    """Complete portfolio risk assessment."""
    total_positions: int
    net_exposure: float
    gross_exposure: float
    currency_exposures: Dict[str, float]
    correlation_matrix: Dict[str, Dict[str, float]]
    concentration: float
    portfolio_var: float
    expected_shortfall: float
    is_excessive: bool
    rejection_reason: Optional[str] = None

class PortfolioEngine:
    """THE portfolio risk engine. Detects common exposure across trades."""
    
    def __init__(self, max_concentration: float = 0.30, 
                 max_currency_exposure: float = 0.20,
                 max_correlation: float = 0.70):
        self.max_concentration = max_concentration
        self.max_currency_exposure = max_currency_exposure
        self.max_correlation = max_correlation
        self.positions: List[dict] = []
    
    def add_position(self, pair: str, direction: str, volume: float, entry_price: float):
        """Add position to portfolio."""
        base, quote = pair[:3], pair[3:]
        self.positions.append({
            "pair": pair, "base": base, "quote": quote,
            "direction": direction, "volume": volume, "entry_price": entry_price,
        })
    
    def clear_positions(self):
        self.positions = []
    
    def calculate_currency_exposures(self) -> Dict[str, float]:
        """Calculate net exposure per currency."""
        exposures = {}
        for pos in self.positions:
            base = pos["base"]
            quote = pos["quote"]
            notional = pos["volume"] * pos["entry_price"] * 100000
            
            if pos["direction"] == "BUY":
                # Long base, short quote
                exposures[base] = exposures.get(base, 0) + notional
                exposures[quote] = exposures.get(quote, 0) - notional
            else:  # SELL
                # Short base, long quote
                exposures[base] = exposures.get(base, 0) - notional
                exposures[quote] = exposures.get(quote, 0) + notional
        
        return exposures
    
    def calculate_correlation(self) -> float:
        """Calculate average correlation across positions."""
        if len(self.positions) < 2:
            return 0.0
        
        # Simplified: pairs sharing the same base or quote have higher correlation
        shared_currency_count = 0
        total_pairs = 0
        
        for i, pos1 in enumerate(self.positions):
            for pos2 in self.positions[i+1:]:
                total_pairs += 1
                if (pos1["base"] == pos2["base"] or pos1["quote"] == pos2["quote"]):
                    shared_currency_count += 1
        
        return shared_currency_count / total_pairs if total_pairs > 0 else 0.0
    
    def calculate_portfolio_var(self, confidence: float = 0.95) -> float:
        """Simplified portfolio VaR."""
        if not self.positions:
            return 0.0
        
        total_notional = sum(
            p["volume"] * p["entry_price"] * 100000 for p in self.positions
        )
        
        # Simplified: 1% daily volatility per position
        daily_vol = total_notional * 0.01
        var = daily_vol * 1.645  # 95% confidence z-score
        return var
    
    def calculate_expected_shortfall(self, var: float) -> float:
        """Expected shortfall (CVaR) - loss beyond VaR."""
        return var * 1.4  # Simplified: ES is typically 40% above VaR
    
    def assess_portfolio_risk(self) -> PortfolioRisk:
        """Complete portfolio risk assessment."""
        exposures = self.calculate_currency_exposures()
        correlation = self.calculate_correlation()
        var = self.calculate_portfolio_var()
        es = self.calculate_expected_shortfall(var)
        
        total_notional = sum(abs(e) for e in exposures.values()) / 2  # Divide by 2 (each trade counted twice)
        net_exposure = sum(exposures.values())
        gross_exposure = sum(abs(e) for e in exposures.values())
        
        # Concentration: largest currency exposure / total gross
        max_exposure = max(exposures.values(), key=abs) if exposures else 0
        concentration = abs(max_exposure) / gross_exposure if gross_exposure > 0 else 0
        
        # Check limits
        is_excessive = False
        rejection_reason = None
        
        if concentration > self.max_concentration:
            is_excessive = True
            rejection_reason = f"Concentration {concentration:.1%} exceeds {self.max_concentration:.1%}"
        
        if correlation > self.max_correlation:
            is_excessive = True
            rejection_reason = f"Correlation {correlation:.1%} exceeds {self.max_correlation:.1%}"
        
        for curr, exp in exposures.items():
            if abs(exp) / gross_exposure > self.max_currency_exposure:
                is_excessive = True
                rejection_reason = f"{curr} exposure too high"
        
        return PortfolioRisk(
            total_positions=len(self.positions),
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            currency_exposures=exposures,
            correlation_matrix={},  # Simplified
            concentration=concentration,
            portfolio_var=var,
            expected_shortfall=es,
            is_excessive=is_excessive,
            rejection_reason=rejection_reason,
        )
    
    def print_portfolio_report(self):
        """Complete portfolio report."""
        risk = self.assess_portfolio_risk()
        
        print("=" * 70)
        print("  PORTFOLIO RISK REPORT")
        print("=" * 70)
        print(f"\n  Positions: {risk.total_positions}")
        print(f"  Net Exposure: ${risk.net_exposure:,.0f}")
        print(f"  Gross Exposure: ${risk.gross_exposure:,.0f}")
        
        print(f"\n  CURRENCY EXPOSURES:")
        for curr, exp in sorted(risk.currency_exposures.items(), key=lambda x: abs(x[1]), reverse=True):
            print(f"    {curr}: ${exp:,.0f}")
        
        print(f"\n  CORRELATION: {self.calculate_correlation():.1%}")
        print(f"  CONCENTRATION: {risk.concentration:.1%}")
        print(f"  VaR (95%): ${risk.portfolio_var:,.0f}")
        print(f"  Expected Shortfall: ${risk.expected_shortfall:,.0f}")
        
        if risk.is_excessive:
            print(f"\n  [RISK] EXCESSIVE: {risk.rejection_reason}")
        else:
            print(f"\n  [OK] Portfolio risk within limits")
        print("=" * 70)


if __name__ == "__main__":
    pf = PortfolioEngine()
    
    # Advisor's example: 3 trades with common USD exposure
    print("\n  ADVISOR'S EXAMPLE:")
    print("  EURUSD SELL + GBPUSD SELL + USDJPY BUY")
    print("  Common USD exposure detected\n")
    
    pf.add_position("EURUSD", "SELL", 0.01, 1.1550)
    pf.add_position("GBPUSD", "SELL", 0.01, 1.3100)
    pf.add_position("USDJPY", "BUY", 0.01, 155.00)
    
    pf.print_portfolio_report()
    
    print("\n  THE INSIGHT:")
    print("  EURUSD SELL = Long USD (short EUR)")
    print("  GBPUSD SELL = Long USD (short GBP)")
    print("  USDJPY BUY  = Short USD (long JPY)")
    print("  Net USD = +$1155 + $1310 - $1550 = ~$915 LONG USD")
    print("  The portfolio engine detects this concentration!")
