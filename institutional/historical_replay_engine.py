"""
Volume 8.5b: Historical Replay Engine
Feeds historical MT5 data through the full institutional pipeline
to generate simulated trades for accelerated learning.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import List, Dict


class HistoricalReplayEngine:
    """
    Replays historical price data through the institutional pipeline.
    Generates shadow trades without live execution.
    """

    def __init__(self):
        self.results = []

    def replay_pair(self, pair: str, days_back: int = 30,
                    timeframe=mt5.TIMEFRAME_M15) -> List[Dict]:
        """
        Replay historical data for a single pair.

        Args:
            pair: Trading pair (e.g., 'USDJPY')
            days_back: How many days of history to replay
            timeframe: MT5 timeframe

        Returns:
            List of simulated trade results
        """
        symbol = pair + 'm'
        mt5.symbol_select(symbol, True)

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days_back)

        rates = mt5.copy_rates_range(symbol, timeframe, start, end)

        if rates is None or len(rates) < 200:
            print(f'  {pair}: Insufficient data ({len(rates) if rates else 0} bars)')
            return []

        df = pd.DataFrame(rates)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        trades = []
        window_size = 200

        for i in range(window_size, len(df) - 1, 20):  # Step every 20 candles (~5 hours)
            window = df.iloc[i-window_size:i].copy()
            window.set_index('time', inplace=True)

            current_price = float(df['close'].iloc[i])
            next_close = float(df['close'].iloc[min(i+20, len(df)-1)])  # ~5h forward

            try:
                # Run through institutional pipeline
                from institutional.market_microstructure import MarketMicrostructure
                from institutional.liquidity_intelligence import LiquidityIntelligence
                from institutional.institutional_structure import InstitutionalStructure
                from institutional.market_regime_engine import MarketRegimeEngine
                from institutional.trade_scorer import scorer

                mm = MarketMicrostructure()
                liq = LiquidityIntelligence()
                struct = InstitutionalStructure()
                regime_engine = MarketRegimeEngine()

                ms = mm.analyze(pair, window)
                lq = liq.analyze(pair, window)
                st = struct.analyze(pair, window)
                regime = regime_engine.analyze(pair, window, ms, lq, st)

                # Generate simple signal based on microstructure
                signal_direction = None
                if ms.institutional_bias == 'BULLISH' and ms.dealer_pressure in ('BUYING_PRESSURE', 'ACCUMULATING'):
                    signal_direction = 'BUY'
                elif ms.institutional_bias == 'BEARISH' and ms.dealer_pressure in ('SELLING_PRESSURE', 'DISTRIBUTING'):
                    signal_direction = 'SELL'

                if signal_direction and lq.sweep_detected:
                    # Build signal
                    signal = {
                        'signal': signal_direction,
                        'confidence': ms.continuation_probability,
                        'entry': current_price,
                        'stop_loss': current_price * 0.998 if signal_direction == 'BUY' else current_price * 1.002,
                        'take_profit': current_price * 1.004 if signal_direction == 'BUY' else current_price * 0.996,
                        'strength': 'STRONG' if ms.continuation_probability > 0.55 else 'MEDIUM',
                        'institutional_bias': ms.institutional_bias,
                        'institutional_score': ms.microstructure_score,
                        'dealer_pressure': ms.dealer_pressure,
                        'liquidity_state': lq.liquidity_state,
                        'continuation_prob': ms.continuation_probability,
                        'regime': regime.regime
                    }

                    # Score the trade
                    quality = scorer.score_trade(pair, signal)

                    # Check regime suitability
                    buy_ok, _ = regime_engine.is_trade_suitable(regime, signal_direction)

                    if quality.recommendation != 'SKIP' and buy_ok:
                        # Simulate outcome
                        if signal_direction == 'BUY':
                            pnl = (next_close - current_price) / current_price * 100  # Percentage
                            result = 'WIN' if next_close > current_price else 'LOSS'
                        else:
                            pnl = (current_price - next_close) / current_price * 100
                            result = 'WIN' if next_close < current_price else 'LOSS'

                        trades.append({
                            'pair': pair,
                            'signal': signal_direction,
                            'confidence': signal['confidence'],
                            'grade': quality.grade,
                            'score': quality.total_score,
                            'regime': regime.regime,
                            'pnl_pct': round(pnl, 4),
                            'result': result,
                            'dealer_pressure': ms.dealer_pressure,
                            'liquidity_state': lq.liquidity_state
                        })

            except Exception as e:
                continue

        return trades

    def run_replay(self, pairs: List[str] = None, days_back: int = 30):
        """Run replay for multiple pairs."""
        if pairs is None:
            pairs = ['USDJPY', 'EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD', 'USDCAD']

        mt5.initialize()
        all_trades = []

        for pair in pairs:
            print(f'Replaying {pair}...')
            trades = self.replay_pair(pair, days_back)
            all_trades.extend(trades)
            print(f'  Generated {len(trades)} simulated trades')

        mt5.shutdown()

        # Save to database
        if all_trades:
            self._save_to_db(all_trades)

        # Print summary
        if all_trades:
            wins = sum(1 for t in all_trades if t['result'] == 'WIN')
            wr = wins / len(all_trades) * 100
            print(f'\n=== REPLAY SUMMARY ===')
            print(f'Total simulated trades: {len(all_trades)}')
            print(f'Wins: {wins} | Losses: {len(all_trades)-wins}')
            print(f'Win Rate: {wr:.1f}%')

            # By pair
            from collections import Counter
            pair_counts = Counter(t['pair'] for t in all_trades)
            for pair, count in pair_counts.most_common():
                pair_trades = [t for t in all_trades if t['pair'] == pair]
                pair_wins = sum(1 for t in pair_trades if t['result'] == 'WIN')
                print(f'  {pair}: {count} trades, {pair_wins/count*100:.0f}% WR')

            # By regime
            regime_trades = {}
            for t in all_trades:
                r = t['regime']
                if r not in regime_trades:
                    regime_trades[r] = {'count': 0, 'wins': 0}
                regime_trades[r]['count'] += 1
                if t['result'] == 'WIN':
                    regime_trades[r]['wins'] += 1
            print(f'\nBy Regime:')
            for regime, stats in sorted(regime_trades.items()):
                print(f'  {regime}: {stats["count"]} trades, {stats["wins"]/stats["count"]*100:.0f}% WR')

        return all_trades

    def _save_to_db(self, trades: List[Dict]):
        """Save simulated trades to shadow_trades table."""
        import sqlite3
        conn = sqlite3.connect('ai-service/trades.db')
        c = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        for t in trades:
            c.execute("""INSERT INTO shadow_trades
                (timestamp, pair, signal, confidence, entry, stop_loss, take_profit,
                 decision, grade, regime, opportunity_score,
                 institutional_bias, institutional_score, dealer_pressure, liquidity_state, continuation_prob,
                 simulated_pnl, simulated_result, session)
                VALUES (?, ?, ?, ?, 0, 0, 0, 'SIMULATED', ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, 'REPLAY')""",
                (now, t['pair'], t['signal'], t['confidence'],
                 t['grade'], t['regime'], t['score'],
                 t.get('institutional_bias', 'UNKNOWN'),
                 t.get('institutional_score', 0),
                 t.get('dealer_pressure', 'UNKNOWN'),
                 t.get('liquidity_state', 'UNKNOWN'),
                 t.get('continuation_prob', 0.5),
                 t['pnl_pct'], t['result']))

        conn.commit()
        count = c.execute("SELECT COUNT(*) FROM shadow_trades WHERE decision='SIMULATED'").fetchone()[0]
        print(f'Saved {count} simulated trades to shadow_trades')
        conn.close()


if __name__ == '__main__':
    engine = HistoricalReplayEngine()
    engine.run_replay(days_back=30)
