"""
Volume 9 Module 2: Pair Intelligence
Converts strategy memory into pair quality scores.
Dynamic - reads from database, not hardcoded.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import Dict, List, Tuple
from institutional.strategy_memory import StrategyMemory


class PairIntelligence:
    """
    Evaluates pair quality based on accumulated strategy memory.
    
    Quality Levels:
        FAVOR    - WR >= 50%, trades >= 5
        NORMAL   - WR >= 40%, trades >= 3
        CAUTION  - WR >= 30%, trades >= 3
        BLOCK    - WR < 30% or insufficient data
    """

    def __init__(self):
        self.memory = StrategyMemory()
        self.min_trades_favor = 5
        self.min_trades_evaluate = 3

    def evaluate_all_pairs(self) -> List[Dict]:
        """Evaluate all pairs in memory"""
        conn = self.memory._init_db.__self__ if hasattr(self.memory._init_db, '__self__') else None
        
        import sqlite3
        conn = sqlite3.connect(self.memory.db_path)
        c = conn.cursor()
        
        c.execute("SELECT DISTINCT pair FROM strategy_memory")
        pairs = [row[0] for row in c.fetchall()]
        conn.close()

        results = []
        for pair in pairs:
            score = self.evaluate_pair(pair)
            results.append(score)

        results.sort(key=lambda x: x['win_rate'], reverse=True)
        return results

    def evaluate_pair(self, pair: str) -> Dict:
        """Evaluate a single pair's quality"""
        import sqlite3
        conn = sqlite3.connect(self.memory.db_path)
        c = conn.cursor()

        # Aggregate all patterns for this pair
        c.execute('''SELECT SUM(trades), SUM(wins), AVG(win_rate), AVG(avg_pnl)
                     FROM strategy_memory WHERE pair = ? AND trades >= ?''',
                  (pair, self.min_trades_evaluate))
        row = c.fetchone()

        total_trades = row[0] or 0
        total_wins = row[1] or 0
        avg_wr = round(row[2], 1) if row[2] else 0
        avg_pnl = round(row[3], 2) if row[3] else 0

        # Get best and worst regimes for this pair
        c.execute('''SELECT regime, signal, trades, win_rate FROM strategy_memory
                     WHERE pair = ? AND trades >= ? ORDER BY win_rate DESC LIMIT 3''',
                  (pair, self.min_trades_evaluate))
        best_regimes = [{'regime': r[0], 'signal': r[1], 'trades': r[2], 'wr': r[3]} for r in c.fetchall()]

        c.execute('''SELECT regime, signal, trades, win_rate FROM strategy_memory
                     WHERE pair = ? AND trades >= ? ORDER BY win_rate ASC LIMIT 3''',
                  (pair, self.min_trades_evaluate))
        worst_regimes = [{'regime': r[0], 'signal': r[1], 'trades': r[2], 'wr': r[3]} for r in c.fetchall()]

        conn.close()

        # Determine quality
        wr = total_wins / total_trades * 100 if total_trades > 0 else 0
        
        if wr >= 50 and total_trades >= self.min_trades_favor:
            quality = "FAVOR"
            adjustment = +10
        elif wr >= 40 and total_trades >= self.min_trades_evaluate:
            quality = "NORMAL"
            adjustment = 0
        elif wr >= 30 and total_trades >= self.min_trades_evaluate:
            quality = "CAUTION"
            adjustment = -10
        else:
            quality = "BLOCK"
            adjustment = -999  # Effectively blocks the trade

        return {
            'pair': pair,
            'quality': quality,
            'win_rate': round(wr, 1),
            'total_trades': total_trades,
            'total_wins': total_wins,
            'avg_pnl': avg_pnl,
            'confidence_adjustment': adjustment,
            'best_regimes': best_regimes,
            'worst_regimes': worst_regimes,
        }

    def should_trade(self, pair: str) -> Tuple[bool, str, float]:
        """
        Quick check: should we trade this pair?
        Returns: (allowed, reason, confidence_adjustment)
        """
        evaluation = self.evaluate_pair(pair)
        quality = evaluation['quality']

        if quality == "FAVOR":
            return True, f"Favored pair ({evaluation['win_rate']}% WR)", evaluation['confidence_adjustment']
        elif quality == "NORMAL":
            return True, f"Normal pair ({evaluation['win_rate']}% WR)", evaluation['confidence_adjustment']
        elif quality == "CAUTION":
            return True, f"Caution - reduced size ({evaluation['win_rate']}% WR)", evaluation['confidence_adjustment']
        else:
            return False, f"Blocked - poor performance ({evaluation['win_rate']}% WR, {evaluation['total_trades']} trades)", evaluation['confidence_adjustment']

    def summary(self):
        """Print pair intelligence summary"""
        pairs = self.evaluate_all_pairs()

        print("=" * 55)
        print("  PAIR INTELLIGENCE - Volume 9 Module 2")
        print("=" * 55)
        print("  Pairs evaluated: " + str(len(pairs)))
        print()
        print("  Pair         Quality   WR      Trades   Adj")
        print("  " + "-" * 48)

        for p in pairs:
            q_mark = {"FAVOR": "++", "NORMAL": "  ", "CAUTION": " -", "BLOCK": "XX"}
            marker = q_mark.get(p['quality'], "??")
            print("  " + marker + " " + p['pair'].ljust(10) + p['quality'].ljust(9) +
                  str(p['win_rate']).ljust(7) + str(p['total_trades']).ljust(8) +
                  (f"+{p['confidence_adjustment']}" if p['confidence_adjustment'] > 0 else str(p['confidence_adjustment'])))

        print()
        print("  Best overall: " + pairs[0]['pair'] + " (" + str(pairs[0]['win_rate']) + "% WR)")
        if pairs[0]['best_regimes']:
            br = pairs[0]['best_regimes'][0]
            print("    Top pattern: " + br['regime'] + " + " + br['signal'] + " = " + str(br['wr']) + "% WR")

        worst = pairs[-1]
        print("\n  Worst overall: " + worst['pair'] + " (" + str(worst['win_rate']) + "% WR)")
        if worst['worst_regimes']:
            wr = worst['worst_regimes'][0]
            print("    Worst pattern: " + wr['regime'] + " + " + wr['signal'] + " = " + str(wr['wr']) + "% WR")

        print("=" * 55)


if __name__ == "__main__":
    pi = PairIntelligence()
    pi.summary()

    # Quick tests
    print("\n  Trade checks:")
    for pair in ["USDJPY", "NZDUSD", "EURUSD", "AUDUSD"]:
        allowed, reason, adj = pi.should_trade(pair)
        status = "ALLOW" if allowed else "BLOCK"
        print("    " + pair + ": " + status + " | " + reason + " | adj=" + str(adj))
