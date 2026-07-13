"""
Volume 9 Module 3: Regime Optimizer
Teaches the system: "When should I trade based on market conditions?"
Dynamic - reads from strategy memory, not hardcoded.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
from typing import Dict, List, Tuple
from institutional.strategy_memory import StrategyMemory


class RegimeOptimizer:
    """
    Evaluates market regime quality and provides confidence adjustments.
    
    Combines with pair intelligence for granular: PAIR + REGIME + DIRECTION scoring.
    """

    def __init__(self):
        self.memory = StrategyMemory()
        self.min_trades = 3

    def evaluate_all_regimes(self) -> List[Dict]:
        """Evaluate all regimes across all pairs"""
        conn = sqlite3.connect(self.memory.db_path)
        c = conn.cursor()

        c.execute('''SELECT regime, SUM(trades), SUM(wins), AVG(win_rate), AVG(avg_pnl)
                     FROM strategy_memory WHERE trades >= ?
                     GROUP BY regime ORDER BY AVG(win_rate) DESC''', (self.min_trades,))
        
        results = []
        for row in c.fetchall():
            regime = row[0]
            trades = row[1]
            wins = row[2]
            wr = round(wins / trades * 100, 1) if trades > 0 else 0
            avg_pnl = round(row[4], 2) if row[4] else 0

            # Calculate adjustment
            if wr >= 55:
                adjustment = +15
                action = "BOOST"
            elif wr >= 48:
                adjustment = +10
                action = "FAVOR"
            elif wr >= 40:
                adjustment = 0
                action = "NEUTRAL"
            elif wr >= 30:
                adjustment = -10
                action = "REDUCE"
            else:
                adjustment = -20
                action = "BLOCK"

            results.append({
                'regime': regime,
                'trades': trades,
                'wins': wins,
                'win_rate': wr,
                'avg_pnl': avg_pnl,
                'adjustment': adjustment,
                'action': action
            })

        conn.close()
        return results

    def evaluate_regime_for_pair(self, pair: str, regime: str) -> Dict:
        """Get granular regime performance for a specific pair"""
        conn = sqlite3.connect(self.memory.db_path)
        c = conn.cursor()

        c.execute('''SELECT signal, trades, wins, win_rate, avg_pnl
                     FROM strategy_memory 
                     WHERE pair = ? AND regime = ? AND trades >= ?
                     ORDER BY win_rate DESC''', (pair, regime, self.min_trades))
        
        signals = []
        total_trades = 0
        total_wins = 0
        
        for row in c.fetchall():
            signals.append({
                'signal': row[0],
                'trades': row[1],
                'wins': row[2],
                'win_rate': row[3],
                'avg_pnl': row[4]
            })
            total_trades += row[1]
            total_wins += row[2]

        conn.close()

        overall_wr = round(total_wins / total_trades * 100, 1) if total_trades > 0 else 0

        # Determine action
        if overall_wr >= 60:
            action = "BOOST"
            adjustment = +15
        elif overall_wr >= 50:
            action = "FAVOR"
            adjustment = +10
        elif overall_wr >= 40:
            action = "NEUTRAL"
            adjustment = 0
        elif overall_wr >= 30:
            action = "REDUCE"
            adjustment = -10
        elif total_trades >= self.min_trades:
            action = "BLOCK"
            adjustment = -20
        else:
            action = "UNKNOWN"
            adjustment = 0

        return {
            'pair': pair,
            'regime': regime,
            'total_trades': total_trades,
            'total_wins': total_wins,
            'win_rate': overall_wr,
            'action': action,
            'adjustment': adjustment,
            'signals': signals
        }

    def should_trade_in_regime(self, pair: str, regime: str, signal: str = None) -> Tuple[bool, str, float]:
        """
        Check if we should trade this pair in this regime.
        Returns: (allowed, reason, confidence_adjustment)
        """
        evaluation = self.evaluate_regime_for_pair(pair, regime)

        if signal and evaluation['signals']:
            # Find specific signal match
            for s in evaluation['signals']:
                if s['signal'] == signal:
                    if s['win_rate'] >= 60:
                        return True, f"Strong {pair}+{regime}+{signal} ({s['win_rate']}% WR, {s['trades']} trades)", +15
                    elif s['win_rate'] >= 45:
                        return True, f"Good {pair}+{regime}+{signal} ({s['win_rate']}% WR)", +5
                    elif s['win_rate'] >= 30:
                        return True, f"Marginal {pair}+{regime}+{signal} - caution", -10
                    else:
                        return False, f"Blocked {pair}+{regime}+{signal} ({s['win_rate']}% WR)", -20

        # General regime evaluation
        action = evaluation['action']
        if action in ("BOOST", "FAVOR"):
            return True, f"{regime} regime favorable for {pair} ({evaluation['win_rate']}% WR)", evaluation['adjustment']
        elif action == "NEUTRAL":
            return True, f"{regime} regime neutral for {pair}", evaluation['adjustment']
        elif action == "REDUCE":
            return True, f"{regime} regime risky for {pair} - reduced size", evaluation['adjustment']
        elif action == "BLOCK":
            return False, f"{regime} regime blocked for {pair} ({evaluation['win_rate']}% WR)", evaluation['adjustment']
        else:
            return True, f"Insufficient data for {pair}+{regime}", 0

    def get_best_regimes_for_pair(self, pair: str, top_n: int = 3) -> List[Dict]:
        """Get best performing regimes for a pair"""
        conn = sqlite3.connect(self.memory.db_path)
        c = conn.cursor()
        c.execute('''SELECT regime, SUM(trades), SUM(wins), AVG(win_rate)
                     FROM strategy_memory WHERE pair = ? AND trades >= ?
                     GROUP BY regime ORDER BY AVG(win_rate) DESC LIMIT ?''',
                  (pair, self.min_trades, top_n))
        results = []
        for row in c.fetchall():
            wr = round(row[2] / row[1] * 100, 1) if row[1] > 0 else 0
            results.append({'regime': row[0], 'trades': row[1], 'win_rate': wr})
        conn.close()
        return results

    def summary(self):
        """Print regime optimizer summary"""
        regimes = self.evaluate_all_regimes()

        print("=" * 55)
        print("  REGIME OPTIMIZER - Volume 9 Module 3")
        print("=" * 55)
        print("  Regimes evaluated: " + str(len(regimes)))
        print()
        print("  Regime         Trades   WR      Action    Adj")
        print("  " + "-" * 48)

        for r in regimes:
            marker = {"BOOST": "++", "FAVOR": " +", "NEUTRAL": "  ", "REDUCE": " -", "BLOCK": "XX"}
            m = marker.get(r['action'], "??")
            print("  " + m + " " + str(r['regime']).ljust(14) + str(r['trades']).ljust(8) +
                  str(r['win_rate']).ljust(7) + r['action'].ljust(9) +
                  (f"+{r['adjustment']}" if r['adjustment'] > 0 else str(r['adjustment'])))

        # Best and worst regime-pair combos
        print("\n  Best regime x pair combos:")
        conn = sqlite3.connect(self.memory.db_path)
        c = conn.cursor()
        c.execute('''SELECT pair, regime, signal, trades, win_rate FROM strategy_memory
                     WHERE trades >= 5 ORDER BY win_rate DESC LIMIT 5''')
        for row in c.fetchall():
            print("    " + row[0] + " + " + row[1] + " + " + row[2] + " = " + str(row[4]) + "% WR (" + str(row[3]) + " trades)")

        print("\n  Worst regime x pair combos:")
        c.execute('''SELECT pair, regime, signal, trades, win_rate FROM strategy_memory
                     WHERE trades >= 5 ORDER BY win_rate ASC LIMIT 5''')
        for row in c.fetchall():
            print("    " + row[0] + " + " + row[1] + " + " + row[2] + " = " + str(row[4]) + "% WR (" + str(row[3]) + " trades)")
        conn.close()

        print("=" * 55)


if __name__ == "__main__":
    ro = RegimeOptimizer()
    ro.summary()

    # Test trade checks
    print("\n  Trade checks:")
    tests = [
        ("NZDUSD", "RANGING", "SELL"),
        ("NZDUSD", "BREAKOUT", "BUY"),
        ("USDJPY", "RANGING", "BUY"),
        ("AUDUSD", "BREAKOUT", "SELL"),
        ("GBPUSD", "RANGING", "BUY"),
    ]
    for pair, regime, signal in tests:
        allowed, reason, adj = ro.should_trade_in_regime(pair, regime, signal)
        status = "ALLOW" if allowed else "BLOCK"
        print("    " + status.ljust(6) + pair + "+" + regime + "+" + signal + " | " + reason + " | adj=" + str(adj))
