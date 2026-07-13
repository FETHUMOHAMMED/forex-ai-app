"""
Phase 10: Adaptive Learning Engine
Learns from every trade outcome and suggests parameter adjustments.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-service'))

import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class LearningInsight:
    """Insight learned from trade data"""
    category: str           # confidence, session, pair, bias, etc.
    finding: str            # What was learned
    confidence: float       # How confident (0-1)
    recommendation: str     # What to change
    expected_impact: str    # HIGH, MEDIUM, LOW


class AdaptiveLearningEngine:
    """
    Analyzes closed trades to find patterns and suggest improvements.
    
    Learns from:
    - Confidence vs outcome correlation
    - Session performance
    - Pair performance
    - Institutional bias accuracy
    - Continuation probability accuracy
    - Time-based patterns
    """
    
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'trades.db')
        self.insights_file = os.path.join(os.path.dirname(__file__), 'learned_insights.json')
        self.min_trades_for_insight = 10
    
    def analyze(self) -> List[LearningInsight]:
        """Run full analysis and return all insights"""
        insights = []
        
        insights.extend(self._analyze_confidence_thresholds())
        insights.extend(self._analyze_session_performance())
        insights.extend(self._analyze_pair_performance())
        insights.extend(self._analyze_institutional_accuracy())
        insights.extend(self._analyze_continuation_accuracy())
        insights.extend(self._analyze_time_patterns())
        
        # Save insights
        self._save_insights(insights)
        
        return insights
    
    def _analyze_confidence_thresholds(self) -> List[LearningInsight]:
        """Find optimal confidence threshold"""
        conn = sqlite3.connect(self.db_path)
        
        insights = []
        
        # Check win rate by confidence bucket
        query = """
        SELECT 
            CASE 
                WHEN confidence >= 0.60 THEN '0.60+'
                WHEN confidence >= 0.55 THEN '0.55-0.60'
                WHEN confidence >= 0.52 THEN '0.52-0.55'
                ELSE '<0.52'
            END as bucket,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
            ROUND(AVG(pnl), 2) as avg_pnl
        FROM trades 
        WHERE pnl IS NOT NULL
        GROUP BY bucket
        ORDER BY bucket
        """
        
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()
        
        best_bucket = None
        best_wr = 0
        
        for row in rows:
            bucket, trades, wins, avg_pnl = row
            wr = (wins / trades * 100) if trades > 0 else 0
            
            if trades >= self.min_trades_for_insight and wr > best_wr:
                best_wr = wr
                best_bucket = bucket
        
        if best_bucket and best_wr > 50:
            insights.append(LearningInsight(
                category="confidence",
                finding=f"Best performance at confidence {best_bucket} with {best_wr:.0f}% win rate",
                confidence=min(0.9, best_wr / 100),
                recommendation=f"Set minimum confidence to {best_bucket.split('+')[0] if '+' in best_bucket else best_bucket.split('-')[0]}",
                expected_impact="HIGH"
            ))
        
        conn.close()
        return insights
    
    def _analyze_session_performance(self) -> List[LearningInsight]:
        """Find best and worst trading sessions"""
        conn = sqlite3.connect(self.db_path)
        insights = []
        
        query = """
        SELECT 
            CASE 
                WHEN CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 0 AND 6 THEN 'ASIAN'
                WHEN CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 7 AND 12 THEN 'LONDON'
                WHEN CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 13 AND 16 THEN 'OVERLAP'
                ELSE 'NY'
            END as session,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(pnl), 2) as total_pnl
        FROM trades 
        WHERE pnl IS NOT NULL
        GROUP BY session
        ORDER BY total_pnl DESC
        """
        
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()
        
        if len(rows) >= 2:
            best = rows[0]
            worst = rows[-1]
            
            if best[0] != worst[0] and best[1] >= self.min_trades_for_insight:
                insights.append(LearningInsight(
                    category="session",
                    finding=f"Best session: {best[0]} (WR: {best[2]/best[1]*100:.0f}%, PnL: ${best[3]:.2f})",
                    confidence=0.7,
                    recommendation=f"Prioritize {best[0]} session, reduce {worst[0]} session trading",
                    expected_impact="MEDIUM"
                ))
        
        conn.close()
        return insights
    
    def _analyze_pair_performance(self) -> List[LearningInsight]:
        """Identify best and worst pairs"""
        conn = sqlite3.connect(self.db_path)
        insights = []
        
        query = """
        SELECT pair, COUNT(*) as trades,
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
               ROUND(SUM(pnl), 2) as total_pnl,
               ROUND(AVG(pnl), 2) as avg_pnl
        FROM trades WHERE pnl IS NOT NULL
        GROUP BY pair
        HAVING trades >= ?
        ORDER BY total_pnl DESC
        """
        
        c = conn.cursor()
        c.execute(query, (self.min_trades_for_insight,))
        rows = c.fetchall()
        
        profitable = [r for r in rows if r[3] and r[3] > 0]
        losing = [r for r in rows if r[3] and r[3] < 0]
        
        if losing:
            worst_pair = losing[-1]
            insights.append(LearningInsight(
                category="pair",
                finding=f"Worst pair: {worst_pair[0]} ({worst_pair[1]} trades, PnL: ${worst_pair[3]:.2f})",
                confidence=0.8,
                recommendation=f"Consider removing {worst_pair[0]} from trading",
                expected_impact="HIGH"
            ))
        
        conn.close()
        return insights
    
    def _analyze_institutional_accuracy(self) -> List[LearningInsight]:
        """Check if institutional bias predicts outcomes"""
        conn = sqlite3.connect(self.db_path)
        insights = []
        
        query = """
        SELECT institutional_bias, COUNT(*) as trades,
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
        FROM trades WHERE pnl IS NOT NULL 
          AND institutional_bias IS NOT NULL
          AND institutional_bias != 'NEUTRAL'
        GROUP BY institutional_bias
        HAVING trades >= 5
        """
        
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()
        
        for row in rows:
            bias, trades, wins = row
            wr = (wins / trades * 100) if trades > 0 else 0
            
            if bias == 'BULLISH' and wr > 55:
                insights.append(LearningInsight(
                    category="institutional",
                    finding=f"Bullish institutional bias predicts {wr:.0f}% win rate",
                    confidence=min(0.9, wr/100),
                    recommendation="Trust BULLISH institutional signals",
                    expected_impact="MEDIUM"
                ))
            elif bias == 'BEARISH' and wr < 45:
                insights.append(LearningInsight(
                    category="institutional",
                    finding=f"Bearish institutional bias predicts {wr:.0f}% win rate (fade opportunity)",
                    confidence=min(0.9, (100-wr)/100),
                    recommendation="Fade BEARISH signals or increase confidence threshold",
                    expected_impact="MEDIUM"
                ))
        
        conn.close()
        return insights
    
    def _analyze_continuation_accuracy(self) -> List[LearningInsight]:
        """Check if continuation probability predicts outcomes"""
        conn = sqlite3.connect(self.db_path)
        insights = []
        
        query = """
        SELECT 
            CASE WHEN continuation_prob >= 0.60 THEN 'HIGH'
                 WHEN continuation_prob >= 0.50 THEN 'MEDIUM'
                 ELSE 'LOW'
            END as bucket,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
            ROUND(AVG(pnl), 2) as avg_pnl
        FROM trades WHERE pnl IS NOT NULL 
          AND continuation_prob IS NOT NULL
        GROUP BY bucket
        HAVING trades >= 5
        """
        
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()
        
        for row in rows:
            bucket, trades, wins, avg_pnl = row
            wr = (wins / trades * 100) if trades > 0 else 0
            
            if bucket == 'HIGH' and wr > 55:
                insights.append(LearningInsight(
                    category="continuation",
                    finding=f"High continuation probability (>60%) predicts {wr:.0f}% win rate",
                    confidence=0.75,
                    recommendation="Increase position size on high continuation signals",
                    expected_impact="MEDIUM"
                ))
        
        conn.close()
        return insights
    
    def _analyze_time_patterns(self) -> List[LearningInsight]:
        """Find time-based patterns"""
        conn = sqlite3.connect(self.db_path)
        insights = []
        
        # Best day of week
        query = """
        SELECT 
            CASE CAST(strftime('%w', timestamp) AS INTEGER)
                WHEN 0 THEN 'Sunday'
                WHEN 1 THEN 'Monday'
                WHEN 2 THEN 'Tuesday'
                WHEN 3 THEN 'Wednesday'
                WHEN 4 THEN 'Thursday'
                WHEN 5 THEN 'Friday'
                WHEN 6 THEN 'Saturday'
            END as day,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(pnl), 2) as total_pnl
        FROM trades WHERE pnl IS NOT NULL
        GROUP BY day
        HAVING trades >= 5
        ORDER BY total_pnl DESC
        """
        
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()
        
        if rows:
            best_day = rows[0]
            if best_day[3] and best_day[3] > 0:
                insights.append(LearningInsight(
                    category="time",
                    finding=f"Best trading day: {best_day[0]} (PnL: ${best_day[3]:.2f})",
                    confidence=0.6,
                    recommendation=f"Increase activity on {best_day[0]}",
                    expected_impact="LOW"
                ))
        
        conn.close()
        return insights
    
    def _save_insights(self, insights: List[LearningInsight]):
        """Save insights to file"""
        data = []
        for i in insights:
            data.append({
                'category': i.category,
                'finding': i.finding,
                'confidence': i.confidence,
                'recommendation': i.recommendation,
                'expected_impact': i.expected_impact,
                'timestamp': datetime.now().isoformat()
            })
        
        # Load existing
        existing = []
        if os.path.exists(self.insights_file):
            with open(self.insights_file, 'r') as f:
                existing = json.load(f)
        
        # Append new and keep last 50
        existing.extend(data)
        if len(existing) > 50:
            existing = existing[-50:]
        
        with open(self.insights_file, 'w') as f:
            json.dump(existing, f, indent=2)
    
    def print_insights(self):
        """Print all current insights"""
        insights = self.analyze()
        
        print("=" * 60)
        print("  ADAPTIVE LEARNING ENGINE - INSIGHTS")
        print("=" * 60)
        
        if not insights:
            print("  No insights yet. Need more trade data.")
            return
        
        for i, insight in enumerate(insights, 1):
            print(f"\n  Insight #{i} [{insight.expected_impact} IMPACT]")
            print(f"  Category: {insight.category}")
            print(f"  Finding: {insight.finding}")
            print(f"  Confidence: {insight.confidence:.0%}")
            print(f"  Recommendation: {insight.recommendation}")
        
        print()
        print("=" * 60)
        print(f"  Total insights: {len(insights)}")
        print(f"  HIGH impact: {sum(1 for i in insights if i.expected_impact == 'HIGH')}")
        print(f"  MEDIUM impact: {sum(1 for i in insights if i.expected_impact == 'MEDIUM')}")
        print(f"  LOW impact: {sum(1 for i in insights if i.expected_impact == 'LOW')}")


if __name__ == '__main__':
    engine = AdaptiveLearningEngine()
    engine.print_insights()