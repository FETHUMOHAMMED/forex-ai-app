"""
Volume 9 Module 1: Strategy Memory
Stores historical patterns: pair + regime + session + signal -> win_rate
This is the experience database for adaptive optimization.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


class StrategyMemory:
    """
    Queryable memory of historical strategy performance.
    Reads from shadow_trades + trades tables to build pattern database.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-service", "trades.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create strategy memory table if not exists"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS strategy_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT NOT NULL,
            regime TEXT NOT NULL,
            session TEXT,
            signal TEXT NOT NULL,
            trades INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0,
            avg_pnl REAL DEFAULT 0,
            total_pnl REAL DEFAULT 0,
            avg_confidence REAL DEFAULT 0,
            avg_score REAL DEFAULT 0,
            last_updated TEXT,
            UNIQUE(pair, regime, session, signal)
        )''')
        conn.commit()
        conn.close()

    def build_from_data(self):
        """Populate strategy memory from all available data sources"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Source 1: Real trades with institutional data
        c.execute('''SELECT pair, institutional_bias as regime, 
                     CASE 
                         WHEN CAST(substr(timestamp,12,2) AS INTEGER) < 7 THEN 'ASIAN'
                         WHEN CAST(substr(timestamp,12,2) AS INTEGER) < 17 THEN 'LONDON'
                         ELSE 'NY'
                     END as session,
                     signal, pnl, institutional_score
                     FROM trades WHERE pnl IS NOT NULL AND institutional_bias IS NOT NULL''')
        self._process_rows(c.fetchall(), conn, "real")

        # Source 2: Shadow simulated trades
        c.execute('''SELECT pair, regime, 
                     CASE WHEN session='REPLAY' THEN 'LONDON' ELSE session END as session,
                     signal, simulated_pnl, opportunity_score
                     FROM shadow_trades WHERE decision='SIMULATED' AND simulated_result != 'PENDING' ''')
        self._process_rows(c.fetchall(), conn, "shadow")

        conn.commit()

        # Count total patterns
        c.execute("SELECT COUNT(*) FROM strategy_memory")
        total = c.fetchone()[0]
        conn.close()

        return total

    def _process_rows(self, rows, conn, source: str):
        """Process trade rows into strategy memory patterns"""
        c = conn.cursor()

        for row in rows:
            if len(row) < 6:
                continue

            pair = row[0]
            regime = row[1] if row[1] else "UNKNOWN"
            session = row[2] if row[2] else "UNKNOWN"
            signal = row[3] if row[3] else "UNKNOWN"
            pnl = float(row[4]) if row[4] else 0
            score = float(row[5]) if len(row) > 5 and row[5] else 0

            win = 1 if pnl > 0 else 0
            now = datetime.now(timezone.utc).isoformat()

            # Upsert using simpler approach
            c.execute("SELECT id, trades, wins, total_pnl, avg_score FROM strategy_memory WHERE pair=? AND regime=? AND session=? AND signal=?", 
                     (pair, regime, session, signal))
            existing = c.fetchone()
            
            if existing:
                new_trades = existing[1] + 1
                new_wins = existing[2] + win
                new_total_pnl = (existing[3] or 0) + pnl
                new_avg_score = ((existing[4] or 0) * existing[1] + score) / new_trades
                new_wr = round(new_wins / new_trades * 100, 1)
                new_avg_pnl = round(new_total_pnl / new_trades, 2)
                
                c.execute("UPDATE strategy_memory SET trades=?, wins=?, win_rate=?, avg_pnl=?, total_pnl=?, avg_score=?, last_updated=? WHERE id=?",
                         (new_trades, new_wins, new_wr, new_avg_pnl, new_total_pnl, new_avg_score, now, existing[0]))
            else:
                c.execute("INSERT INTO strategy_memory (pair, regime, session, signal, trades, wins, win_rate, avg_pnl, total_pnl, avg_score, last_updated) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)",
                         (pair, regime, session, signal, win, round(win*100, 1), pnl, pnl, score, now))

        conn.commit()

    def query(self, pair: str = None, regime: str = None,
              session: str = None, signal: str = None,
              min_trades: int = 3) -> List[Dict]:
        """Query strategy memory with filters"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        query = "SELECT * FROM strategy_memory WHERE trades >= ?"
        params = [min_trades]

        if pair:
            query += " AND pair = ?"
            params.append(pair)
        if regime:
            query += " AND regime = ?"
            params.append(regime)
        if session:
            query += " AND session = ?"
            params.append(session)
        if signal:
            query += " AND signal = ?"
            params.append(signal)

        query += " ORDER BY win_rate DESC"
        c.execute(query, params)

        columns = [desc[0] for desc in c.description]
        results = [dict(zip(columns, row)) for row in c.fetchall()]
        conn.close()
        return results

    def get_best_patterns(self, min_trades: int = 5, top_n: int = 10) -> List[Dict]:
        """Get top performing patterns"""
        return self.query(min_trades=min_trades)[:top_n]

    def get_worst_patterns(self, min_trades: int = 5, top_n: int = 10) -> List[Dict]:
        """Get worst performing patterns"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT * FROM strategy_memory WHERE trades >= ?
                     ORDER BY win_rate ASC LIMIT ?''', (min_trades, top_n))
        columns = [desc[0] for desc in c.description]
        results = [dict(zip(columns, row)) for row in c.fetchall()]
        conn.close()
        return results

    def get_pair_score(self, pair: str) -> float:
        """Get aggregate win rate for a pair (0-100)"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT SUM(wins), SUM(trades) FROM strategy_memory
                     WHERE pair = ? AND trades >= 3''', (pair,))
        row = c.fetchone()
        conn.close()
        if row and row[1] and row[1] > 0:
            return round(row[0] / row[1] * 100, 1)
        return 50.0  # Default neutral

    def summary(self):
        """Print memory summary"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM strategy_memory")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(DISTINCT pair) FROM strategy_memory")
        pairs = c.fetchone()[0]

        c.execute("SELECT COUNT(DISTINCT regime) FROM strategy_memory")
        regimes = c.fetchone()[0]

        print("=" * 50)
        print("  STRATEGY MEMORY - Volume 9 Module 1")
        print("=" * 50)
        print("  Patterns stored: " + str(total))
        print("  Pairs tracked: " + str(pairs))
        print("  Regimes tracked: " + str(regimes))

        c.execute('''SELECT pair, regime, signal, trades, win_rate
                     FROM strategy_memory WHERE trades >= 5
                     ORDER BY win_rate DESC LIMIT 5''')
        print("\n  Top 5 Patterns:")
        for row in c.fetchall():
            print("    " + str(row[0]).ljust(10) + str(row[1]).ljust(15) + str(row[2]).ljust(6) +
                  str(row[3]).ljust(6) + str(row[4]) + "% WR")

        c.execute('''SELECT pair, regime, signal, trades, win_rate
                     FROM strategy_memory WHERE trades >= 5
                     ORDER BY win_rate ASC LIMIT 5''')
        print("\n  Worst 5 Patterns:")
        for row in c.fetchall():
            print("    " + str(row[0]).ljust(10) + str(row[1]).ljust(15) + str(row[2]).ljust(6) +
                  str(row[3]).ljust(6) + str(row[4]) + "% WR")

        print("=" * 50)
        conn.close()


if __name__ == "__main__":
    memory = StrategyMemory()
    count = memory.build_from_data()
    memory.summary()

    # Test queries
    print("\n  Query: NZDUSD + RANGING")
    results = memory.query(pair="NZDUSD", regime="RANGING", min_trades=1)
    for r in results:
        print("    " + r['signal'] + ": " + str(r['trades']) + " trades, " + str(r['win_rate']) + "% WR")

    print("\n  Pair Scores:")
    for pair in ["USDJPY", "NZDUSD", "EURUSD", "GBPUSD", "USDCAD", "AUDUSD"]:
        score = memory.get_pair_score(pair)
        print("    " + pair + ": " + str(score) + "%")
