"""
Shadow Trade Outcome Simulator
For rejected trades, simulates what WOULD have happened:
- Did price hit TP first? = WIN
- Did price hit SL first? = LOSS
- Neither hit? = Check current PnL
This teaches the AI which rejections were mistakes.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone, timedelta


class ShadowSimulator:
    """Simulates outcomes for rejected shadow trades using historical MT5 data."""

    def __init__(self, db_path: str = "ai-service/trades.db"):
        self.db_path = db_path

    def simulate_all_pending(self):
        """Simulate outcomes for all shadow trades with PENDING result."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''SELECT id, pair, signal, entry, stop_loss, take_profit, timestamp
                     FROM shadow_trades WHERE simulated_result='PENDING'
                     ORDER BY id DESC LIMIT 100''')
        pending = c.fetchall()
        conn.close()

        if not pending:
            return 0

        mt5.initialize()
        simulated = 0

        for row in pending:
            shadow_id, pair, signal, entry, sl, tp, ts = row

            try:
                outcome, exit_price, pnl = self._simulate_outcome(pair, entry, sl, tp, ts, signal)
                self._update_outcome(shadow_id, exit_price, pnl, outcome)
                simulated += 1
            except Exception as e:
                pass  # Skip if can't simulate (old data, missing symbol, etc.)

        mt5.shutdown()
        return simulated

    def _simulate_outcome(self, pair: str, entry: float, sl: float, tp: float,
                          timestamp: str, direction: str) -> tuple:
        """Simulate whether TP or SL would have been hit first."""
        symbol = pair + 'm'
        mt5.symbol_select(symbol, True)

        # Parse timestamp and get data from that point onward
        try:
            trade_dt = datetime.fromisoformat(timestamp)
            if trade_dt.tzinfo is None:
                trade_dt = trade_dt.replace(tzinfo=timezone.utc)
        except:
            trade_dt = datetime.now(timezone.utc) - timedelta(hours=24)

        end_dt = datetime.now(timezone.utc)

        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, trade_dt, end_dt)

        if rates is None or len(rates) < 2:
            return 'PENDING', entry, 0

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        # Check candle by candle: did TP or SL hit first?
        tp_hit = False
        sl_hit = False
        exit_price = entry

        for i in range(len(df)):
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]

            if direction == 'BUY':
                if high >= tp and not sl_hit:
                    tp_hit = True
                    exit_price = tp
                    break
                if low <= sl and not tp_hit:
                    sl_hit = True
                    exit_price = sl
                    break
            else:  # SELL
                if low <= tp and not sl_hit:
                    tp_hit = True
                    exit_price = tp
                    break
                if high >= sl and not tp_hit:
                    sl_hit = True
                    exit_price = sl
                    break

        # Calculate PnL
        if direction == 'BUY':
            pnl = (exit_price - entry) * 100000  # Standard lot approximation
        else:
            pnl = (entry - exit_price) * 100000

        if tp_hit:
            return 'WIN', exit_price, pnl
        elif sl_hit:
            return 'LOSS', exit_price, pnl
        else:
            # Neither hit yet - use current price
            current = df['close'].iloc[-1]
            if direction == 'BUY':
                pnl = (current - entry) * 100000
            else:
                pnl = (entry - current) * 100000
            return 'PENDING', current, pnl

    def _update_outcome(self, shadow_id: int, exit_price: float, pnl: float, result: str):
        """Update shadow trade with simulated outcome."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''UPDATE shadow_trades SET simulated_pnl=?, simulated_result=?
                     WHERE id=?''', (pnl, result, shadow_id))
        conn.commit()
        conn.close()

    def get_learning_stats(self):
        """Get statistics on rejected trades that would have won."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Rejected trades that would have been winners
        c.execute('''SELECT COUNT(*), SUM(simulated_pnl)
                     FROM shadow_trades
                     WHERE decision='REJECT' AND simulated_result='WIN' ''')
        missed_wins, missed_pnl = c.fetchone()

        # Rejected trades that were correct rejections (would have lost)
        c.execute('''SELECT COUNT(*), SUM(simulated_pnl)
                     FROM shadow_trades
                     WHERE decision='REJECT' AND simulated_result='LOSS' ''')
        correct_rejections, saved_loss = c.fetchone()

        conn.close()

        return {
            'missed_wins': missed_wins or 0,
            'missed_pnl': round(missed_pnl or 0, 2),
            'correct_rejections': correct_rejections or 0,
            'saved_loss': round(abs(saved_loss or 0), 2)
        }


if __name__ == '__main__':
    sim = ShadowSimulator()
    count = sim.simulate_all_pending()
    print(f'Simulated {count} pending shadow trades')

    stats = sim.get_learning_stats()
    print(f'\nLearning Stats:')
    print(f'  Missed wins (rejected but won): {stats["missed_wins"]} (PnL: {stats["missed_pnl"]})')
    print(f'  Correct rejections (would have lost): {stats["correct_rejections"]} (Saved: {stats["saved_loss"]})')
