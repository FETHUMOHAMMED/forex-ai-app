"""
Phase 7: Institutional Trade Quality Scorer
Combines ML, ICT, and Microstructure into a single trade quality score.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dataclasses import dataclass
from typing import Optional

@dataclass
class TradeQualityScore:
    """Composite trade quality assessment"""
    pair: str
    signal: str
    
    # Component scores (0-100 each)
    ml_score: float = 0.0          # Based on ML confidence
    ict_score: float = 0.0         # Based on ICT pattern strength
    institutional_score: float = 0.0  # Based on microstructure
    trend_score: float = 0.0       # Based on H1/H4 alignment
    
    # Final composite
    total_score: float = 0.0       # Weighted average
    grade: str = "F"               # A, B, C, D, F
    recommendation: str = "SKIP"   # TRADE, CAUTIOUS, SKIP
    
    # Explanation
    reasons: list = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


class TradeScorer:
    """
    Combines all signal components into a single trade quality score.
    
    Weights:
    - ML Confidence: 25%
    - ICT Confirmation: 25%
    - Institutional Bias: 30%
    - Trend Alignment: 20%
    """
    
    def __init__(self):
        # Scoring thresholds
        self.ML_WEIGHT = 0.25
        self.ICT_WEIGHT = 0.25
        self.INST_WEIGHT = 0.30
        self.TREND_WEIGHT = 0.20
        
        # Minimum thresholds for trade
        self.MIN_TOTAL_SCORE = 40  # Minimum composite score to trade
        self.MIN_INST_SCORE = 20   # Minimum institutional score
    
    def score_trade(self, pair: str, signal: dict) -> TradeQualityScore:
        """
        Calculate composite trade quality score.
        
        Args:
            pair: Trading pair
            signal: Signal dictionary containing ML, ICT, institutional data
        
        Returns:
            TradeQualityScore with full assessment
        """
        result = TradeQualityScore(
            pair=pair,
            signal=signal.get('signal', 'UNKNOWN')
        )
        
        # 1. ML Confidence Score (0-100)
        ml_conf = signal.get('confidence', 0.50)
        if ml_conf >= 0.70:
            result.ml_score = 90
        elif ml_conf >= 0.65:
            result.ml_score = 75
        elif ml_conf >= 0.60:
            result.ml_score = 60
        elif ml_conf >= 0.55:
            result.ml_score = 45
        elif ml_conf >= 0.52:
            result.ml_score = 35
        elif ml_conf >= 0.50:
            result.ml_score = 25
        else:
            result.ml_score = 10
        
        # 2. ICT Score (0-100)
        strength = signal.get('strength', 'WEAK')
        if strength == 'STRONG':
            result.ict_score = 85
        elif strength == 'MEDIUM':
            result.ict_score = 60
        elif strength == 'WEAK':
            result.ict_score = 35
        else:
            result.ict_score = 15
        
        # 3. Institutional Score (0-100)
        inst_bias = signal.get('institutional_bias', 'NEUTRAL')
        inst_score = signal.get('institutional_score', 0)
        cont_prob = signal.get('continuation_prob', 0.50)
        
        # Convert institutional_score (-100 to +100) to 0-100 scale
        inst_normalized = (inst_score + 100) / 2  # Now 0-100
        
        # Adjust based on alignment with trade direction
        if signal.get('signal') == 'BUY' and inst_bias == 'BULLISH':
            inst_normalized = min(100, inst_normalized + 15)
            result.reasons.append("Institutional bias aligned with BUY")
        elif signal.get('signal') == 'SELL' and inst_bias == 'BEARISH':
            inst_normalized = min(100, inst_normalized + 15)
            result.reasons.append("Institutional bias aligned with SELL")
        elif inst_bias == 'NEUTRAL':
            result.reasons.append("Institutional bias neutral - no edge from microstructure")
        
        # Continuation bonus
        if cont_prob > 0.65:
            inst_normalized = min(100, inst_normalized + 10)
            result.reasons.append(f"High continuation probability ({cont_prob:.0%})")
        
        result.institutional_score = inst_normalized
        
        # 4. Trend Score (0-100)
        regime = signal.get('regime', 'volatile')
        # Trend-aligned signals get bonus (from H1 filter)
        if signal.get('signal') == 'BUY':
            result.trend_score = 70  # Default
            result.reasons.append("Trend assessment: default for BUY")
        else:
            result.trend_score = 70
            result.reasons.append("Trend assessment: default for SELL")
        
        # Calculate weighted total
        result.total_score = (
            result.ml_score * self.ML_WEIGHT +
            result.ict_score * self.ICT_WEIGHT +
            result.institutional_score * self.INST_WEIGHT +
            result.trend_score * self.TREND_WEIGHT
        )
        
        # Assign grade
        if result.total_score >= 80:
            result.grade = "A"
            result.recommendation = "TRADE"
        elif result.total_score >= 65:
            result.grade = "B"
            result.recommendation = "TRADE"
        elif result.total_score >= 55:
            result.grade = "C"
            result.recommendation = "CAUTIOUS"
        elif result.total_score >= 40:
            result.grade = "D"
            result.recommendation = "CAUTIOUS"
        else:
            result.grade = "F"
            result.recommendation = "SKIP"
        
        # Override: skip if institutional score too low
        if result.institutional_score < self.MIN_INST_SCORE:
            result.recommendation = "SKIP"
            result.reasons.append("Institutional score below minimum threshold")
        
        return result


# Singleton for easy import
scorer = TradeScorer()