"""
Volume 4: Institutional Risk & Capital Allocation Engine
Answers: HOW MUCH capital should we commit?
Dynamic risk sizing based on institutional score, market conditions, and account state.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Tuple

@dataclass
class RiskAllocation:
    """Institutional risk allocation decision"""
    pair: str
    timestamp: str
    
    # Risk assessment
    risk_score: float = 0.0              # 0-100
    recommended_risk_pct: float = 0.0    # e.g., 0.35 = 0.35%
    position_size: float = 0.0           # Lot size
    allocation_state: str = "REJECT"     # FULL, REDUCED, MINIMAL, REJECT
    
    # Component scores
    institutional_quality: float = 0.0   # 0-100
    market_condition_score: float = 0.0  # 0-100
    account_health_score: float = 0.0    # 0-100
    
    # Drawdown state
    drawdown_state: str = "NORMAL"       # NORMAL, CAUTION, REDUCE, STOP
    current_drawdown_pct: float = 0.0
    
    # Exposure
    portfolio_exposure: float = 0.0      # Current total exposure %
    max_allowed_exposure: float = 5.0    # Maximum exposure %
    
    # Reasons
    risk_factors: List[str] = field(default_factory=list)
    capital_allocation_reason: str = ""


class InstitutionalRiskEngine:
    """
    Institutional capital allocation engine.
    
    Determines optimal position size based on:
    - Institutional score (Volumes 1-3 combined)
    - Market conditions (volatility, session, regime)
    - Account health (drawdown, exposure, streak)
    """
    
    def __init__(self, base_risk: float = 1.0, max_risk: float = 2.0):
        self.base_risk = base_risk          # Base risk % (e.g., 1.0 = 1%)
        self.max_risk = max_risk            # Maximum risk %
        self.min_risk = 0.10                # Minimum risk %
        
        # Drawdown thresholds
        self.DD_NORMAL = 3.0    # Normal trading below 3%
        self.DD_CAUTION = 6.0   # Reduce risk above 6%
        self.DD_REDUCE = 10.0   # Minimal risk above 10%
        self.DD_STOP = 15.0     # Stop trading above 15%
    
    def calculate_allocation(self, pair: str, signal: dict, 
                             account_balance: float = 100000,
                             current_drawdown: float = 0.0,
                             current_exposure: float = 0.0) -> RiskAllocation:
        """
        Calculate optimal risk allocation for a trade.
        
        Args:
            pair: Trading pair
            signal: Signal dict with institutional data
            account_balance: Current account balance
            current_drawdown: Current drawdown percentage
            current_exposure: Current portfolio exposure percentage
        
        Returns:
            RiskAllocation with full risk assessment
        """
        result = RiskAllocation(
            pair=pair,
            timestamp=datetime.now(timezone.utc).isoformat(),
            current_drawdown_pct=current_drawdown,
            portfolio_exposure=current_exposure,
            max_allowed_exposure=5.0
        )
        
        # 1. Assess institutional quality (Volumes 1-3 combined)
        inst_score = signal.get('institutional_score', 50)
        structure_score = signal.get('structure_score', 0)  # From Volume 3
        liquidity_score = signal.get('liquidity_score', 0)  # From Volume 2
        
        result.institutional_quality = self._assess_institutional_quality(
            inst_score, structure_score, liquidity_score
        )
        
        # 2. Assess market conditions
        ml_conf = signal.get('confidence', 0.50)
        cont_prob = signal.get('continuation_prob', 0.50)
        regime = signal.get('regime', 'volatile')
        
        result.market_condition_score = self._assess_market_conditions(
            ml_conf, cont_prob, regime
        )
        
        # 3. Assess account health
        result.drawdown_state = self._assess_drawdown(current_drawdown)
        result.account_health_score = self._assess_account_health(
            current_drawdown, current_exposure
        )
        
        # 4. Calculate composite risk score
        result.risk_score = (
            result.institutional_quality * 0.45 +
            result.market_condition_score * 0.30 +
            result.account_health_score * 0.25
        )
        
        # 5. Calculate recommended risk
        result.recommended_risk_pct = self._calculate_risk_pct(
            result.risk_score, result.drawdown_state
        )
        
        # 6. Calculate position size
        stop_distance = abs(signal.get('entry', 0) - signal.get('stop_loss', 0))
        result.position_size = self._calculate_position_size(
            account_balance, result.recommended_risk_pct, stop_distance, pair
        )
        
        # 7. Determine allocation state
        result.allocation_state = self._determine_allocation_state(
            result.risk_score, result.drawdown_state, current_exposure
        )
        
        # 8. Build risk factors
        result.risk_factors = self._build_risk_factors(result)
        result.capital_allocation_reason = self._build_reason(result)
        
        return result
    
    def _assess_institutional_quality(self, inst_score: float, structure_score: float, 
                                      liquidity_score: float) -> float:
        """Combine Volumes 1-3 into institutional quality score (0-100)"""
        # Normalize structure_score from -100/100 to 0/100
        struct_norm = (structure_score + 100) / 2 if structure_score else 50
        
        # Weighted combination
        quality = inst_score * 0.4 + struct_norm * 0.35 + (liquidity_score + 100) / 2 * 0.25
        
        return max(0, min(100, quality))
    
    def _assess_market_conditions(self, ml_conf: float, cont_prob: float, 
                                   regime: str) -> float:
        """Assess market condition quality (0-100)"""
        score = 50.0
        
        # ML confidence contribution
        if ml_conf >= 0.70:
            score += 20
        elif ml_conf >= 0.60:
            score += 10
        elif ml_conf < 0.52:
            score -= 15
        
        # Continuation probability
        if cont_prob >= 0.70:
            score += 15
        elif cont_prob < 0.45:
            score -= 10
        
        # Regime adjustment
        if regime == 'trending':
            score += 5
        elif regime == 'volatile':
            score -= 10
        
        return max(0, min(100, score))
    
    def _assess_drawdown(self, dd_pct: float) -> str:
        """Determine drawdown state"""
        if dd_pct >= self.DD_STOP:
            return "STOP"
        elif dd_pct >= self.DD_REDUCE:
            return "REDUCE"
        elif dd_pct >= self.DD_CAUTION:
            return "CAUTION"
        return "NORMAL"
    
    def _assess_account_health(self, dd_pct: float, exposure: float) -> float:
        """Assess account health (0-100)"""
        score = 100.0
        
        # Drawdown penalty
        if dd_pct > 0:
            score -= dd_pct * 3  # -3 points per 1% drawdown
        
        # Exposure penalty
        if exposure > 3.0:
            score -= (exposure - 3.0) * 10
        
        return max(0, min(100, score))
    
    def _calculate_risk_pct(self, risk_score: float, dd_state: str) -> float:
        """Calculate recommended risk percentage"""
        # Base risk from score
        if risk_score >= 80:
            base = self.base_risk * 1.2
        elif risk_score >= 65:
            base = self.base_risk
        elif risk_score >= 50:
            base = self.base_risk * 0.5
        elif risk_score >= 35:
            base = self.base_risk * 0.25
        else:
            base = 0
        
        # Drawdown multiplier
        if dd_state == "STOP":
            base = 0
        elif dd_state == "REDUCE":
            base *= 0.1
        elif dd_state == "CAUTION":
            base *= 0.4
        
        return max(0, min(self.max_risk, base))
    
    def _calculate_position_size(self, balance: float, risk_pct: float, 
                                  stop_distance: float, pair: str) -> float:
        """Calculate position size in lots"""
        if risk_pct <= 0 or stop_distance <= 0 or balance <= 0:
            return 0.0
        
        risk_amount = balance * (risk_pct / 100)
        
        # Pip value approximation
        pip_value = 0.01 if 'JPY' in pair else 0.0001
        sl_pips = stop_distance / pip_value if pip_value > 0 else 0
        
        if sl_pips <= 0:
            return 0.0
        
        # Standard lot: 1 pip = $10
        lot_size = risk_amount / (sl_pips * 10)
        
        return round(max(0.01, min(1.0, lot_size)), 2)
    
    def _determine_allocation_state(self, risk_score: float, dd_state: str, 
                                     exposure: float) -> str:
        """Determine final allocation state"""
        if dd_state == "STOP":
            return "REJECT"
        if risk_score < 35:
            return "REJECT"
        if exposure >= 5.0:
            return "REJECT"
        if risk_score >= 70 and dd_state == "NORMAL":
            return "FULL"
        if risk_score >= 50:
            return "REDUCED"
        return "MINIMAL"
    
    def _build_risk_factors(self, result: RiskAllocation) -> List[str]:
        """Build list of risk factors"""
        factors = []
        
        if result.institutional_quality < 50:
            factors.append("Weak institutional quality")
        if result.market_condition_score < 50:
            factors.append("Poor market conditions")
        if result.drawdown_state != "NORMAL":
            factors.append(f"Drawdown state: {result.drawdown_state}")
        if result.portfolio_exposure > 3.0:
            factors.append(f"High portfolio exposure ({result.portfolio_exposure:.1f}%)")
        if result.risk_score >= 70:
            factors.append("Strong risk profile")
        
        return factors
    
    def _build_reason(self, result: RiskAllocation) -> str:
        """Build capital allocation reason"""
        if result.allocation_state == "REJECT":
            return "Risk profile insufficient for capital allocation"
        elif result.allocation_state == "FULL":
            return f"Strong institutional quality ({result.risk_score:.0f}/100) - full allocation"
        elif result.allocation_state == "REDUCED":
            return f"Moderate quality ({result.risk_score:.0f}/100) - reduced allocation"
        return f"Minimal quality ({result.risk_score:.0f}/100) - minimal allocation"