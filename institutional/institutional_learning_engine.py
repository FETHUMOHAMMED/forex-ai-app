"""
Volume 6: Institutional Learning & Adaptive Intelligence Engine
Learns from every trade to improve future decisions.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dataclasses import dataclass
from typing import Optional
from .setup_memory import query_similar_setups, DB_PATH
import sqlite3

@dataclass
class LearningResult:
    """Learning engine output"""
    pair: str
    direction: str
    
    # Historical evidence
    similar_setups_found: int = 0
    historical_win_rate: float = 0.0
    historical_avg_r: float = 0.0
    
    # Confidence adjustments
    ml_confidence: float = 0.50
    institutional_confidence: float = 0.50
    historical_confidence: float = 0.50
    final_confidence: float = 0.50
    
    # Recommendation
    confidence_adjustment: float = 0.0
    recommendation: str = "NEUTRAL"  # INCREASE, NEUTRAL, DECREASE, SKIP


class InstitutionalLearningEngine:
    """
    Learns from historical trade memory to improve decisions.
    
    Stage 1 (current): Observation mode - analyzes patterns, suggests adjustments
    Stage 2 (future): Auto-evolution - modifies strategy weights
    """
    
    def __init__(self):
        self.min_samples = 5  # Minimum similar setups needed for recommendation
    
    def analyze(self, pair: str, direction: str, signal: dict,
                ms_result=None, liq_result=None, struct_result=None) -> LearningResult:
        """
        Analyze current setup against historical memory.
        """
        result = LearningResult(
            pair=pair,
            direction=direction,
            ml_confidence=signal.get('confidence', 0.50)
        )
        
        # Query similar setups
        market_phase = struct_result.market_phase if struct_result else None
        structure_bias = struct_result.structure_bias if struct_result else None
        
        historical = query_similar_setups(
            pair, direction,
            market_phase=market_phase,
            structure_bias=structure_bias
        )
        
        result.similar_setups_found = historical['total']
        result.historical_win_rate = historical['win_rate']
        result.historical_avg_r = historical['avg_r']
        
        # Calculate institutional confidence from Volumes 1-3
        inst_score = 0.50
        if ms_result and ms_result.continuation_probability:
            inst_score = ms_result.continuation_probability
        if struct_result and struct_result.continuation_probability:
            inst_score = (inst_score + struct_result.continuation_probability) / 2
        result.institutional_confidence = inst_score
        
        # Calculate historical confidence
        if result.similar_setups_found >= self.min_samples:
            result.historical_confidence = result.historical_win_rate / 100
        else:
            result.historical_confidence = 0.50  # Neutral if insufficient data
        
        # Calculate final confidence (weighted)
        result.final_confidence = (
            result.ml_confidence * 0.25 +
            result.institutional_confidence * 0.45 +
            result.historical_confidence * 0.30
        )
        
        # Calculate adjustment
        result.confidence_adjustment = result.final_confidence - result.ml_confidence
        
        # Recommendation
        result.recommendation = self._recommend(result)
        
        return result
    
    def _recommend(self, result: LearningResult) -> str:
        """Generate recommendation based on learning"""
        if result.similar_setups_found < self.min_samples:
            return "NEUTRAL"
        
        if result.historical_win_rate >= 65 and result.historical_avg_r >= 1.5:
            return "INCREASE"
        elif result.historical_win_rate >= 55:
            return "NEUTRAL"
        elif result.historical_win_rate < 40:
            return "SKIP"
        return "DECREASE"
    
    def get_performance_summary(self) -> dict:
        """Get overall learning performance summary"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Overall stats
        c.execute('SELECT COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END), AVG(result_r) FROM trade_memory')
        total, wins, avg_r = c.fetchone()
        
        # By pair
        c.execute('SELECT pair, COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END), AVG(result_r) FROM trade_memory GROUP BY pair ORDER BY COUNT(*) DESC')
        by_pair = c.fetchall()
        
        # By session
        c.execute('SELECT session, COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END) FROM trade_memory GROUP BY session')
        by_session = c.fetchall()
        
        conn.close()
        
        return {
            'total_trades': total or 0,
            'wins': wins or 0,
            'win_rate': (wins / total * 100) if total else 0,
            'avg_r': round(avg_r or 0, 2),
            'by_pair': [(p[0], p[1], round(p[2]/p[1]*100,1) if p[1] else 0, round(p[3],2)) for p in by_pair],
            'by_session': [(s[0], s[1], round(s[2]/s[1]*100,1) if s[1] else 0) for s in by_session]
        }