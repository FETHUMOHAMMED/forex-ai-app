"""
Volume 8.5: Shadow Trading Collector
Records ALL decisions (executed AND rejected) for accelerated learning.
Does NOT send orders to MT5 - records simulated outcomes only.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, Dict, List
import json


@dataclass
class ShadowTrade:
    """A shadow trade record - either executed or rejected"""
    pair: str
    signal: str
    confidence: float
    entry: float
    stop_loss: float
    take_profit: float
    decision: str  # EXECUTED, REJECTED, CAUTIOUS
    grade: str
    regime: str
    opportunity_score: float
    rejection_reason: str = ""
    simulated_pnl: float = 0.0
    simulated_result: str = "PENDING"  # WIN, LOSS, BREAKEVEN, PENDING


class ShadowCollector:
    """
    Records every trading opportunity - win or lose, executed or rejected.
    This is the data accelerator for Volume 9+ learning.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-service", "trades.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create shadow trade tables if not exist"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Shadow trades table
        c.execute('''CREATE TABLE IF NOT EXISTS shadow_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            pair TEXT NOT NULL,
            signal TEXT NOT NULL,
            confidence REAL,
            entry REAL,
            stop_loss REAL,
            take_profit REAL,
            decision TEXT,
            grade TEXT,
            regime TEXT,
            opportunity_score REAL,
            rejection_reason TEXT,
            institutional_bias TEXT,
            institutional_score REAL,
            dealer_pressure TEXT,
            liquidity_state TEXT,
            continuation_prob REAL,
            session TEXT,
            simulated_pnl REAL DEFAULT 0,
            simulated_result TEXT DEFAULT 'PENDING',
            created_at TEXT DEFAULT (datetime('now'))
        )''')

        # Opportunity stats table (aggregated)
        c.execute('''CREATE TABLE IF NOT EXISTS opportunity_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            pair TEXT,
            total_opportunities INTEGER DEFAULT 0,
            executed INTEGER DEFAULT 0,
            rejected INTEGER DEFAULT 0,
            cautious INTEGER DEFAULT 0,
            avg_confidence REAL,
            avg_score REAL,
            top_regime TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )''')

        conn.commit()
        conn.close()

    def record_opportunity(self, pair: str, signal: dict, decision_result: dict,
                           regime_result=None, rejection_reason: str = "") -> int:
        """
        Record a trading opportunity regardless of execution decision.

        Args:
            pair: Trading pair
            signal: Signal dictionary with confidence, entry, SL, TP
            decision_result: Decision engine output (grade, score, decision)
            regime_result: Regime engine output
            rejection_reason: Why it was rejected (if applicable)

        Returns:
            shadow_trade_id
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Extract signal details
        sig_direction = signal.get('signal', 'UNKNOWN')
        confidence = signal.get('confidence', 0.5)
        entry = signal.get('entry', 0)
        sl = signal.get('stop_loss', 0)
        tp = signal.get('take_profit', 0)

        # Extract decision details
        grade = decision_result.get('grade', 'F') if isinstance(decision_result, dict) else getattr(decision_result, 'grade', 'F')
        opp_score = decision_result.get('opportunity_score', 0) if isinstance(decision_result, dict) else getattr(decision_result, 'opportunity_score', 0)
        decision = decision_result.get('decision', 'REJECT') if isinstance(decision_result, dict) else getattr(decision_result, 'decision', 'REJECT')

        # Extract institutional data
        inst_bias = signal.get('institutional_bias', 'UNKNOWN')
        inst_score = signal.get('institutional_score', 0)
        dealer_pressure = signal.get('dealer_pressure', 'UNKNOWN')
        liquidity_state = signal.get('liquidity_state', 'UNKNOWN')
        continuation_prob = signal.get('continuation_prob', 0.5)

        # Session
        hour = datetime.now(timezone.utc).hour
        session = 'ASIAN' if 0 <= hour < 7 else 'LONDON' if 7 <= hour < 17 else 'NY' if 17 <= hour < 20 else 'OVERLAP'

        # Regime
        regime = regime_result.regime if regime_result else 'UNKNOWN'

        now = datetime.now(timezone.utc).isoformat()

        c.execute('''INSERT INTO shadow_trades
            (timestamp, pair, signal, confidence, entry, stop_loss, take_profit,
             decision, grade, regime, opportunity_score, rejection_reason,
             institutional_bias, institutional_score, dealer_pressure,
             liquidity_state, continuation_prob, session)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (now, pair, sig_direction, confidence, entry, sl, tp,
             decision, grade, regime, opp_score, rejection_reason,
             inst_bias, inst_score, dealer_pressure,
             liquidity_state, continuation_prob, session))

        shadow_id = c.lastrowid

        # Update daily stats
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        c.execute('''SELECT id FROM opportunity_stats WHERE date=? AND pair=?''', (today, pair))
        existing = c.fetchone()

        if existing:
            if decision == 'EXECUTE':
                c.execute('UPDATE opportunity_stats SET executed=executed+1, total_opportunities=total_opportunities+1 WHERE date=? AND pair=?', (today, pair))
            elif decision == 'CAUTIOUS':
                c.execute('UPDATE opportunity_stats SET cautious=cautious+1, total_opportunities=total_opportunities+1 WHERE date=? AND pair=?', (today, pair))
            else:
                c.execute('UPDATE opportunity_stats SET rejected=rejected+1, total_opportunities=total_opportunities+1 WHERE date=? AND pair=?', (today, pair))
        else:
            executed = 1 if decision == 'EXECUTE' else 0
            cautious = 1 if decision == 'CAUTIOUS' else 0
            rejected = 1 if decision == 'REJECT' else 0
            c.execute('''INSERT INTO opportunity_stats (date, pair, total_opportunities, executed, rejected, cautious, avg_confidence, avg_score, top_regime)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)''',
                (today, pair, executed, rejected, cautious, confidence, opp_score, regime))

        conn.commit()
        conn.close()
        return shadow_id

    def update_outcome(self, shadow_id: int, exit_price: float, pnl: float):
        """Update shadow trade with simulated outcome"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        result = 'WIN' if pnl > 0 else 'LOSS' if pnl < 0 else 'BREAKEVEN'
        c.execute('''UPDATE shadow_trades SET simulated_pnl=?, simulated_result=?
                     WHERE id=?''', (pnl, result, shadow_id))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """Get shadow trading statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT COUNT(*), decision FROM shadow_trades GROUP BY decision')
        decisions = {row[1]: row[0] for row in c.fetchall()}

        c.execute('SELECT COUNT(*) FROM shadow_trades')
        total = c.fetchone()[0]

        c.execute('SELECT pair, COUNT(*), AVG(confidence), AVG(opportunity_score) FROM shadow_trades GROUP BY pair')
        by_pair = [{'pair': row[0], 'count': row[1], 'avg_conf': round(row[2], 3) if row[2] else 0, 'avg_score': round(row[3], 1) if row[3] else 0} for row in c.fetchall()]

        conn.close()

        return {
            'total_opportunities': total,
            'executed': decisions.get('EXECUTE', 0),
            'rejected': decisions.get('REJECT', 0),
            'cautious': decisions.get('CAUTIOUS', 0),
            'by_pair': by_pair
        }

    def get_rejected_sample(self, limit: int = 20) -> List[Dict]:
        """Get sample of rejected trades for analysis"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT pair, signal, confidence, grade, regime, rejection_reason, opportunity_score
                     FROM shadow_trades WHERE decision='REJECT' ORDER BY id DESC LIMIT ?''', (limit,))
        rows = c.fetchall()
        conn.close()
        return [{'pair': r[0], 'signal': r[1], 'confidence': r[2], 'grade': r[3],
                 'regime': r[4], 'reason': r[5], 'score': r[6]} for r in rows]


# Singleton
collector = ShadowCollector()


# Quick test
if __name__ == "__main__":
    c = ShadowCollector()
    stats = c.get_stats()
    print(f"Shadow DB: {stats['total_opportunities']} total opportunities")
    print(f"  Executed: {stats['executed']}")
    print(f"  Rejected: {stats['rejected']}")
    print(f"  Cautious: {stats['cautious']}")
    if stats['by_pair']:
        for p in stats['by_pair']:
            print(f"  {p['pair']}: {p['count']} ops, avg conf={p['avg_conf']}, avg score={p['avg_score']}")
