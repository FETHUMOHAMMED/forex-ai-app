"""
Volume 5: Institutional Trade Decision Engine
The investment committee - decides WHAT to trade with full reasoning.
Combines Volumes 1-4 into a single institutional-grade decision.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

@dataclass
class InstitutionalDecision:
    """Complete institutional trade decision"""
    pair: str
    signal: str
    timestamp: str
    
    # Decision
    decision: str = "REJECT"          # EXECUTE_BUY, EXECUTE_SELL, REDUCE_SIZE, WATCH, REJECT
    grade: str = "F"                   # A+, A, B, C, D, F
    confidence: float = 0.0           # 0-100%
    
    # Component scores (0-100)
    structure_score: float = 0.0
    liquidity_score: float = 0.0
    microstructure_score: float = 0.0
    risk_score: float = 0.0
    ml_score: float = 0.0
    session_score: float = 0.0
    
    # Total opportunity score
    opportunity_score: float = 0.0    # 0-100
    
    # Expected value
    expected_value_r: float = 0.0     # In R multiples
    win_probability: float = 0.50
    
    # Risk
    recommended_risk_pct: float = 0.0
    invalidation_level: Optional[float] = None
    
    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    decision_rationale: str = ""


class TradeDecisionEngine:
    """
    Institutional investment committee.
    
    Combines all 4 volumes into a final decision:
    - EXECUTE: Full size
    - REDUCE_SIZE: Half size
    - WATCH: Don't trade but monitor
    - REJECT: No trade
    """
    
    def __init__(self):
        # Component weights for opportunity scoring
        self.weights = {
            'structure': 0.25,
            'liquidity': 0.20,
            'microstructure': 0.20,
            'risk': 0.15,
            'ml': 0.10,
            'session': 0.10
        }
        
        # Grade thresholds
        self.grade_thresholds = {
            'A+': 90, 'A': 80, 'B': 70, 'C': 60, 'D': 50, 'F': 0
        }
    
    def decide(self, pair: str, signal: dict, 
               microstructure_result=None,
               liquidity_result=None,
               structure_result=None,
               risk_allocation=None) -> InstitutionalDecision:
        """
        Make institutional trade decision.
        
        Args:
            pair: Trading pair
            signal: Signal dictionary
            microstructure_result: From Volume 1
            liquidity_result: From Volume 2
            structure_result: From Volume 3
            risk_allocation: From Volume 4
        
        Returns:
            InstitutionalDecision with full reasoning
        """
        decision = InstitutionalDecision(
            pair=pair,
            signal=signal.get('signal', 'UNKNOWN'),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # 1. Score each component (0-100)
        decision.structure_score = self._score_structure(structure_result, signal)
        decision.liquidity_score = self._score_liquidity(liquidity_result)
        decision.microstructure_score = self._score_microstructure(microstructure_result)
        decision.risk_score = self._score_risk(risk_allocation)
        decision.ml_score = self._score_ml(signal)
        decision.session_score = self._score_session()
        
        # 2. Calculate opportunity score
        decision.opportunity_score = (
            decision.structure_score * self.weights['structure'] +
            decision.liquidity_score * self.weights['liquidity'] +
            decision.microstructure_score * self.weights['microstructure'] +
            decision.risk_score * self.weights['risk'] +
            decision.ml_score * self.weights['ml'] +
            decision.session_score * self.weights['session']
        )
        
        # 3. Assign grade
        decision.grade = self._assign_grade(decision.opportunity_score)
        
        # 4. Calculate expected value
        decision.win_probability = self._estimate_win_probability(decision)
        avg_win_r = 2.0  # From TP/SL ratio
        avg_loss_r = 1.0
        decision.expected_value_r = (
            decision.win_probability * avg_win_r -
            (1 - decision.win_probability) * avg_loss_r
        )
        
        # 5. Determine decision
        decision.decision = self._determine_decision(decision)
        
        # 6. Set risk
        decision.recommended_risk_pct = self._calculate_decision_risk(decision)
        
        # 7. Set invalidation
        decision.invalidation_level = self._set_invalidation(pair, signal, structure_result)
        
        # 8. Build reasoning
        decision.reasons, decision.warnings = self._build_reasoning(decision, signal)
        decision.decision_rationale = self._build_rationale(decision)
        
        return decision
    
    
    def _score_structure(self, structure_result, signal: dict) -> float:
        """Score structure component (0-100) - calibrated to real analyzers"""
        if structure_result is None:
            return 50

        score = 50.0

        # Phase scoring (uses real fields: structure_bias, market_phase)
        bias = getattr(structure_result, 'structure_bias', 'RANGE')
        phase = getattr(structure_result, 'market_phase', 'STABLE')

        if bias == 'BULLISH_TRENDING' and signal.get('signal') == 'BUY':
            score += 25
        elif bias == 'BEARISH_TRENDING' and signal.get('signal') == 'SELL':
            score += 25
        elif bias in ('BULLISH_WEAK', 'BEARISH_WEAK'):
            score += 5
        elif bias == 'RANGE' or bias == 'RANGE_COMPRESSION':
            score -= 20  # Range markets underperform

        # Phase
        if phase == 'EXPANDING':
            score += 10
        elif phase == 'CONTRACTING':
            score -= 10

        # Continuation probability
        cp = getattr(structure_result, 'continuation_prob', 0.50)
        if cp > 0.60:
            score += 10
        elif cp < 0.45:
            score -= 10

        # Structure score from analyzer
        ss = getattr(structure_result, 'structure_score', 50)
        score += (ss - 50) * 0.3

        return max(0, min(100, score))

    
    
    def _score_liquidity(self, liquidity_result) -> float:
        """Score liquidity component (0-100) - calibrated to real analyzers"""
        if liquidity_result is None:
            return 50

        score = 50.0

        # Sweep detection (real field: sweep_detected)
        sweep = getattr(liquidity_result, 'sweep_detected', False)
        sweep_dir = getattr(liquidity_result, 'sweep_direction', None)

        if sweep:
            score += 20  # Sweeps are predictive (feature analysis proven)
        else:
            score -= 15  # No sweep = lower win rate

        # Liquidity state
        liq_state = getattr(liquidity_result, 'liquidity_state', '')
        if 'SWEEP' in str(liq_state):
            score += 10
        elif liq_state == 'NEAR_LIQUIDITY':
            score -= 5

        # Liquidity score from analyzer
        liq_score = getattr(liquidity_result, 'liquidity_score', 50)
        score += (liq_score - 50) * 0.3

        return max(0, min(100, score))

    
    
    def _score_microstructure(self, ms_result) -> float:
        """Score microstructure component (0-100) - calibrated to real analyzers"""
        if ms_result is None:
            return 50

        score = 50.0

        # Dealer pressure (real field: dealer_pressure)
        dp = getattr(ms_result, 'dealer_pressure', 'NEUTRAL')

        if dp == 'BUYING_PRESSURE':
            score += 15
        elif dp == 'SELLING_PRESSURE':
            score += 15  # Both directional pressures are better than neutral
        elif dp == 'ACCUMULATING':
            score += 8
        elif dp == 'DISTRIBUTING':
            score += 8
        elif dp == 'NEUTRAL':
            score -= 15  # NEUTRAL dealer pressure = 20% WR proven

        # Volume delta
        delta = getattr(ms_result, 'volume_delta', 0)
        if abs(delta) > 0.15:
            score += 10

        # Continuation probability
        cp = getattr(ms_result, 'continuation_probability', 0.50)
        if cp > 0.58:
            score += 8

        # Microstructure score
        ms_score = getattr(ms_result, 'microstructure_score', 50)
        score += (ms_score - 50) * 0.2

        return max(0, min(100, score))

    
    def _score_risk(self, risk_allocation) -> float:
        """Score risk component (0-100)"""
        if risk_allocation is None:
            return 50
        
        # Convert risk allocation quality to score
        if risk_allocation.allocation_state == "FULL":
            return 90
        elif risk_allocation.allocation_state == "REDUCED":
            return 65
        elif risk_allocation.allocation_state == "MINIMAL":
            return 40
        return 20
    
    def _score_ml(self, signal: dict) -> float:
        """Score ML component (0-100)"""
        conf = signal.get('confidence', 0.50)
        
        if conf >= 0.70:
            return 90
        elif conf >= 0.65:
            return 75
        elif conf >= 0.60:
            return 60
        elif conf >= 0.55:
            return 45
        elif conf >= 0.52:
            return 30
        return 15
    
    
    def _score_session(self) -> float:
        """Score session component (0-100) - calibrated to real data"""
        hour = datetime.now(timezone.utc).hour

        if 7 <= hour < 13:       # London: 47% WR, +$48 (BEST)
            return 85
        elif 0 <= hour < 7:      # Asian: 40% WR (acceptable)
            return 50
        elif 13 <= hour < 16:    # Overlap: 21% WR, -$345 (BAD)
            return 25
        elif 16 <= hour < 20:    # NY: 0% WR, -$414 (WORST)
            return 10
        return 20

    
    def _assign_grade(self, score: float) -> str:
        """Assign letter grade"""
        for grade, threshold in self.grade_thresholds.items():
            if score >= threshold:
                return grade
        return "F"
    
    def _estimate_win_probability(self, decision: InstitutionalDecision) -> float:
        """Estimate win probability from opportunity score"""
        # Base 50%, adjust by score
        prob = 0.50 + (decision.opportunity_score - 50) * 0.008
        return max(0.25, min(0.85, prob))
    
    def _determine_decision(self, decision: InstitutionalDecision) -> str:
        """Determine final trade decision"""
        if decision.opportunity_score >= 80:
            return "EXECUTE"
        elif decision.opportunity_score >= 65:
            return "REDUCE_SIZE"
        elif decision.opportunity_score >= 40:
            return "REDUCE_SIZE"
        elif decision.opportunity_score >= 30:
            return "WATCH"
        return "REJECT"
    
    def _calculate_decision_risk(self, decision: InstitutionalDecision) -> float:
        """Calculate risk based on decision grade"""
        if decision.grade in ('A+', 'A'):
            return 0.5
        elif decision.grade == 'B':
            return 0.35
        elif decision.grade == 'C':
            return 0.20
        elif decision.grade == 'D':
            return 0.10
        return 0.0
    
    def _set_invalidation(self, pair: str, signal: dict, structure_result) -> Optional[float]:
        """Set invalidation level"""
        if structure_result is None:
            return None
        
        entry = signal.get('entry', 0)
        # Simple: recent swing low for buys, swing high for sells
        return entry * 0.998 if signal.get('signal') == 'BUY' else entry * 1.002
    
    def _build_reasoning(self, decision: InstitutionalDecision, signal: dict) -> tuple:
        """Build reasons and warnings"""
        reasons = []
        warnings = []
        
        if decision.structure_score >= 60:
            reasons.append("Favorable market structure")
        else:
            warnings.append("Weak market structure")
        
        if decision.liquidity_score >= 60:
            reasons.append("Quality liquidity environment")
        else:
            warnings.append("Poor liquidity conditions")
        
        if decision.microstructure_score >= 60:
            reasons.append("Institutional alignment confirmed")
        
        if decision.ml_score >= 50:
            reasons.append(f"ML confidence: {signal.get('confidence', 0):.0%}")
        else:
            warnings.append(f"Low ML confidence: {signal.get('confidence', 0):.0%}")
        
        if decision.session_score >= 70:
            reasons.append("Active trading session")
        
        if decision.expected_value_r > 0.5:
            reasons.append(f"Positive expected value: {decision.expected_value_r:.1f}R")
        
        return reasons, warnings
    
    def _build_rationale(self, decision: InstitutionalDecision) -> str:
        """Build decision rationale"""
        if decision.decision == "EXECUTE":
            return f"Strong institutional setup (Grade {decision.grade}, Score {decision.opportunity_score:.0f}/100)"
        elif decision.decision == "REDUCE_SIZE":
            return f"Moderate setup (Grade {decision.grade}) - reduced position warranted"
        elif decision.decision == "WATCH":
            return f"Marginal setup (Grade {decision.grade}) - monitor for improvement"
        return f"Insufficient institutional quality (Grade {decision.grade})"