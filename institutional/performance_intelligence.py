"""
Volume 7: Institutional Performance Intelligence
The hedge-fund analyst - measures what makes money and why.
Detects edge, strategy decay, and optimal setups.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'trades.db')

@dataclass
class PerformanceResult:
    """Performance intelligence analysis"""
    pair: str
    timestamp: str
    
    # Historical edge
    similar_trades: int = 0
    historical_win_rate: float = 0.0
    historical_avg_r: float = 0.0
    edge_score: float = 0.0           # 0-100
    
    # Setup quality
    best_setup: str = "UNKNOWN"
    setup_win_rate: float = 0.0
    
    # Winning factors
    winning_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    # Decay detection
    strategy_decay: bool = False
    decay_warning: str = ""
    
    # Recommendations
    confidence_adjustment: float = 0.0
    risk_recommendation: str = "NORMAL"  # INCREASE, NORMAL, REDUCE, SKIP


class PerformanceIntelligence:
    """
    Institutional performance analyst.
    Measures edge, detects strategy decay, identifies winning patterns.
    """
    
    def __init__(self):
        self.min_samples = 10
        self._init_db()
    
    def _init_db(self):
        """Initialize performance memory table"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS performance_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                pair TEXT,
                session TEXT,
                direction TEXT,
                entry_time TEXT,
                exit_time TEXT,
                pnl REAL,
                result_r REAL,
                win_loss TEXT,
                
                institutional_score REAL,
                liquidity_state TEXT,
                structure_phase TEXT,
                dealer_pressure TEXT,
                setup_type TEXT,
                
                decision_quality TEXT,
                success_reason TEXT,
                failure_reason TEXT,
                
                edge_score REAL,
                model_adjustment REAL,
                created_at TEXT
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_perf_pair ON performance_memory(pair)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_perf_setup ON performance_memory(setup_type)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_perf_result ON performance_memory(win_loss)')
        conn.commit()
        conn.close()
    
    def analyze_setup(self, pair: str, direction: str, session: str,
                      liquidity_state: str = None, structure_phase: str = None,
                      dealer_pressure: str = None) -> PerformanceResult:
        """Analyze historical performance for a specific setup"""
        result = PerformanceResult(
            pair=pair,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Find similar trades
        query = 'SELECT COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END), AVG(result_r) FROM trade_memory WHERE pair=? AND direction=?'
        params = [pair, direction]
        
        if session:
            query += ' AND session=?'
            params.append(session)
        
        c.execute(query, params)
        row = c.fetchone()
        result.similar_trades = row[0] or 0
        wins = row[1] or 0
        result.historical_win_rate = (wins / result.similar_trades * 100) if result.similar_trades > 0 else 0
        result.historical_avg_r = round(row[2] or 0, 2)
        
        # Calculate edge score
        if result.similar_trades >= self.min_samples:
            # Edge = win_rate above 50% weighted by avg R
            wr_edge = max(0, result.historical_win_rate - 50) * 1.5
            r_edge = max(0, result.historical_avg_r - 0.5) * 20
            result.edge_score = min(100, wr_edge + r_edge + 50)
        else:
            result.edge_score = 50  # Neutral when insufficient data
        
        # Find best setup
        c.execute('''SELECT setup_type, COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END), AVG(result_r)
                     FROM performance_memory WHERE pair=? GROUP BY setup_type 
                     HAVING COUNT(*) >= 3 ORDER BY AVG(result_r) DESC LIMIT 1''', (pair,))
        best = c.fetchone()
        if best:
            result.best_setup = best[0] or "UNKNOWN"
            result.setup_win_rate = (best[2]/best[1]*100) if best[1] else 0
        
        conn.close()
        
        # Winning factors
        result.winning_factors = self._identify_winning_factors(pair, direction)
        
        # Strategy decay
        result.strategy_decay, result.decay_warning = self._detect_decay(pair)
        
        # Recommendations
        result.confidence_adjustment = self._calculate_adjustment(result)
        result.risk_recommendation = self._risk_recommendation(result)
        
        return result
    
    def _identify_winning_factors(self, pair: str, direction: str) -> List[str]:
        """Identify what makes trades win"""
        factors = []
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Check liquidity sweep impact
        c.execute('''SELECT COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END) 
                     FROM trade_memory WHERE pair=? AND liquidity_event!="NO_LIQUIDITY_EVENT"''', (pair,))
        row = c.fetchone()
        if row[0] and row[0] >= 3:
            sweep_wr = (row[1]/row[0]*100) if row[0] else 0
            if sweep_wr > 55:
                factors.append(f"Liquidity sweep present ({sweep_wr:.0f}% WR)")
        
        # Check structure phase
        c.execute('''SELECT market_phase, COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END)
                     FROM trade_memory WHERE pair=? AND direction=? GROUP BY market_phase
                     HAVING COUNT(*) >= 3 ORDER BY COUNT(*) DESC''', (pair, direction))
        phases = c.fetchall()
        for phase in phases[:2]:
            if phase[0] and phase[1] >= 3:
                wr = (phase[2]/phase[1]*100)
                if wr > 55:
                    factors.append(f"{phase[0]} phase ({wr:.0f}% WR)")
        
        conn.close()
        return factors
    
    def _detect_decay(self, pair: str) -> tuple:
        """Detect strategy performance decay"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Compare recent 20 vs older 20
        c.execute('''SELECT COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END)
                     FROM trade_memory WHERE pair=? ORDER BY id DESC LIMIT 20''', (pair,))
        recent = c.fetchone()
        
        c.execute('''SELECT COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END)
                     FROM trade_memory WHERE pair=? ORDER BY id DESC LIMIT 20 OFFSET 20''', (pair,))
        older = c.fetchone()
        
        conn.close()
        
        if recent[0] and recent[0] >= 10 and older[0] and older[0] >= 10:
            recent_wr = (recent[1]/recent[0]*100) if recent[0] else 0
            older_wr = (older[1]/older[0]*100) if older[0] else 0
            
            if recent_wr < older_wr - 15:
                return True, f"Win rate dropped from {older_wr:.0f}% to {recent_wr:.0f}%"
        
        return False, ""
    
    def _calculate_adjustment(self, result: PerformanceResult) -> float:
        """Calculate confidence adjustment based on historical edge"""
        if result.similar_trades < self.min_samples:
            return 0.0
        
        # Convert edge score to confidence adjustment (-0.15 to +0.15)
        return (result.edge_score - 50) * 0.003
    
    def _risk_recommendation(self, result: PerformanceResult) -> str:
        """Recommend risk level based on edge"""
        if result.strategy_decay:
            return "REDUCE"
        if result.edge_score >= 75:
            return "INCREASE"
        elif result.edge_score >= 55:
            return "NORMAL"
        elif result.edge_score >= 35:
            return "REDUCE"
        return "SKIP"
    
    def log_performance(self, pair: str, direction: str, pnl: float, result_r: float,
                        institutional_score: float = 0, liquidity_state: str = None,
                        structure_phase: str = None, dealer_pressure: str = None,
                        setup_type: str = None, session: str = None,
                        decision_quality: str = None):
        """Log trade performance to memory"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        win_loss = "WIN" if pnl > 0 else "LOSS"
        success_reason = ""
        failure_reason = ""
        
        if pnl > 0:
            success_reason = f"Profitable {setup_type or 'trade'} in {session or 'unknown'} session"
        else:
            failure_reason = f"Loss in {setup_type or 'trade'} - review conditions"
        
        c.execute('''
            INSERT INTO performance_memory (
                timestamp, pair, session, direction, pnl, result_r, win_loss,
                institutional_score, liquidity_state, structure_phase,
                dealer_pressure, setup_type, decision_quality,
                success_reason, failure_reason, edge_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(timezone.utc).isoformat(), pair, session, direction,
            round(pnl, 2), round(result_r, 2), win_loss,
            institutional_score, liquidity_state, structure_phase,
            dealer_pressure, setup_type, decision_quality,
            success_reason, failure_reason, 50,
            datetime.now(timezone.utc).isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Overall
        c.execute('SELECT COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END), AVG(result_r) FROM performance_memory')
        total, wins, avg_r = c.fetchone()
        
        # By setup
        c.execute('''SELECT setup_type, COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END), AVG(result_r)
                     FROM performance_memory WHERE setup_type IS NOT NULL 
                     GROUP BY setup_type HAVING COUNT(*) >= 3 ORDER BY AVG(result_r) DESC''')
        by_setup = c.fetchall()
        
        # By session
        c.execute('''SELECT session, COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END)
                     FROM performance_memory WHERE session IS NOT NULL
                     GROUP BY session ORDER BY COUNT(*) DESC''')
        by_session = c.fetchall()
        
        conn.close()
        
        return {
            'total': total or 0,
            'wins': wins or 0,
            'win_rate': (wins/total*100) if total else 0,
            'avg_r': round(avg_r or 0, 2),
            'by_setup': [(s[0], s[1], round(s[2]/s[1]*100,1) if s[1] else 0, round(s[3],2)) for s in by_setup],
            'by_session': [(s[0], s[1], round(s[2]/s[1]*100,1) if s[1] else 0) for s in by_session]
        }