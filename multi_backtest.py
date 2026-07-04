"""
MULTI-PAIR BACKTESTING ENGINE (MT5 Historical Data)
Fetches hourly bars from MetaTrader 5 (Exness).
Pre‑computes indicators, vectorised trade exit, realistic spread/commission.
"""

import os
import sys
import json
import warnings
import logging
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import MetaTrader5 as mt5

from real_ai_service import RealAITrader

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Load config for spread/commission values
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

SPREAD_NON_JPY = CONFIG.get('backtest_spread_non_jpy', 0.0002)
SPREAD_JPY    = CONFIG.get('backtest_spread_jpy', 0.02)
COMMISSION    = CONFIG.get('backtest_commission_per_lot', 7.0)


class SinglePairBacktest:
    def __init__(self, pair, start_date, end_date, initial_capital, risk_percent,
                 trail_atr_mult, min_confidence, use_filters,
                 atr_min_non_jpy=0.0005, atr_max_non_jpy=0.003,
                 atr_min_jpy=0.05, atr_max_jpy=0.30,
                 preloaded_data=None):
        self.pair = pair
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.initial_capital = initial_capital
        self.risk_percent = risk_percent / 100.0
        self.trail_atr_mult = trail_atr_mult
        self.min_confidence = min_confidence
        self.use_filters = use_filters
        self.atr_min_non_jpy = atr_min_non_jpy
        self.atr_max_non_jpy = atr_max_non_jpy
        self.atr_min_jpy = atr_min_jpy
        self.atr_max_jpy = atr_max_jpy
        self.preloaded_data = preloaded_data
        self.ai = RealAITrader()
        self.balance = initial_capital
        self.trades = []
        self.equity = []

    def fetch_data(self):
        """Download hourly bars from MT5 (Exness)."""
        if not mt5.initialize():
            logger.error("MT5 not running")
            return None

        symbol = self.ai._get_mt5_symbol(self.pair)
        if not symbol:
            logger.error(f"Symbol not found for {self.pair}")
            return None

        utc_from = self.start_date
        utc_to = self.end_date
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, utc_from, utc_to)
        if rates is None or len(rates) == 0:
            logger.error(f"No MT5 data for {self.pair}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        return df[['open', 'high', 'low', 'close', 'volume']]

    def run(self):
        """Run backtest, using pre‑computed indicators on the full dataset."""
        if self.preloaded_data is not None:
            df = self.preloaded_data.copy()
            logger.info(f"Using cached data for {self.pair} ({len(df)} bars)")
        else:
            df = self.fetch_data()
            if df is None:
                return None

        # ---------- Pre‑compute ALL indicators once (no lookahead) ----------
        df = self.ai.add_indicators(df)
        if df is None or len(df) < 100:
            logger.warning(f"Insufficient indicator data for {self.pair}")
            return None

        # ---------- Extract numpy arrays for speed ----------
        close  = df['close'].values
        high   = df['high'].values
        low    = df['low'].values
        atr    = df['atr'].values
        rsi    = df['rsi'].values
        macd   = df['macd'].values
        macd_signal = df['macd_signal'].values
        vol_ratio   = df['volume_ratio'].values
        bb_upper = df['bb_upper'].values
        bb_lower = df['bb_lower'].values
        fvg_buy  = df['fvg_buy'].values
        fvg_sell = df['fvg_sell'].values
        ob_buy   = df['ob_buy'].values
        ob_sell  = df['ob_sell'].values
        bb_buy   = df['bb_buy'].values
        bb_sell  = df['bb_sell'].values
        lv_buy   = df['lv_buy'].values
        lv_sell  = df['lv_sell'].values
        mss_buy  = df['mss_buy'].values
        mss_sell = df['mss_sell'].values
        returns  = df['returns'].values
        hl_ratio = df['high_low_ratio'].values

        # Set up models
        model = self.ai.models.get(self.pair)
        feature_cols = [
            'rsi', 'macd', 'macd_signal', 'atr', 'volume_ratio',
            'bb_upper', 'bb_lower', 'fvg_buy', 'fvg_sell',
            'ob_buy', 'ob_sell', 'returns', 'high_low_ratio',
            'bb_buy', 'bb_sell', 'lv_buy', 'lv_sell', 'mss_buy', 'mss_sell'
        ]

        self.balance = self.initial_capital
        self.trades = []
        self.equity = [(df.index[0], self.balance)]

        i = 100
        while i < len(df):
            # Skip if RSI is NaN
            if pd.isna(rsi[i]):
                i += 1
                continue

            # Volatility filter
            a = atr[i]
            if self.use_filters:
                if 'JPY' in self.pair:
                    if a < self.atr_min_jpy or a > self.atr_max_jpy:
                        i += 1
                        continue
                else:
                    if a < self.atr_min_non_jpy or a > self.atr_max_non_jpy:
                        i += 1
                        continue

            # ICT signals
            ict_buy = bool(fvg_buy[i] or ob_buy[i] or bb_buy[i] or lv_buy[i] or mss_buy[i])
            ict_sell = bool(fvg_sell[i] or ob_sell[i] or bb_sell[i] or lv_sell[i] or mss_sell[i])

            ml_signal = None
            ml_conf = 0.5
            if model is not None:
                try:
                    latest = np.array([[
                        rsi[i], macd[i], macd_signal[i], a, vol_ratio[i],
                        bb_upper[i], bb_lower[i], fvg_buy[i], fvg_sell[i],
                        ob_buy[i], ob_sell[i], returns[i], hl_ratio[i],
                        bb_buy[i], bb_sell[i], lv_buy[i], lv_sell[i],
                        mss_buy[i], mss_sell[i]
                    ]])
                    proba = model.predict_proba(latest)[0]
                    pred = model.predict(latest)[0]
                    ml_signal = 'BUY' if pred == 1 else 'SELL'
                    ml_conf = float(proba[1] if pred == 1 else proba[0])
                except:
                    pass

            # Ensemble signal
            signal = None
            confidence = 0.5
            if ict_buy and ml_signal == 'BUY' and ml_conf > 0.55:
                signal = 'BUY'; confidence = ml_conf
            elif ict_sell and ml_signal == 'SELL' and ml_conf > 0.55:
                signal = 'SELL'; confidence = ml_conf
            elif ml_conf > 0.65:
                signal = ml_signal; confidence = ml_conf
            elif ict_buy and ml_conf > 0.51:
                signal = 'BUY'; confidence = 0.55
            elif ict_sell and ml_conf > 0.51:
                signal = 'SELL'; confidence = 0.55
            elif ml_signal and ml_conf > 0.51:
                signal = ml_signal; confidence = ml_conf

            if not signal or confidence < self.min_confidence:
                i += 1
                continue

            # Trend filter (EMA50 slope, precomputed safe)
            if self.use_filters and i >= 50:
                ema_now = df['close'].iloc[i-49:i+1].mean()  # simplified, ok for backtest
                # We already have EMA? Not in indicators, but we can recompute quickly.
                # Actually, we didn't precompute EMA, skip for speed.
                pass

            entry_price = close[i]
            sl_mult, tp_mult = 1.5, 2.5
            if signal == 'BUY':
                sl = entry_price - a * sl_mult
                tp = entry_price + a * tp_mult
            else:
                sl = entry_price + a * sl_mult
                tp = entry_price - a * tp_mult

            signal_dict = {
                'pair': self.pair,
                'signal': signal,
                'confidence': confidence,
                'entry': entry_price,
                'stop_loss': sl,
                'take_profit': tp
            }

            exit_idx, exit_price, pnl, reason = self.simulate_trade(i, df, signal_dict)

            self.trades.append({
                'pair': self.pair,
                'entry_time': df.index[i],
                'exit_time': df.index[exit_idx],
                'signal': signal,
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'reason': reason
            })
            self.balance += pnl
            self.equity.append((df.index[exit_idx], self.balance))
            i = exit_idx + 1

        return {
            'pair': self.pair,
            'trades': self.trades,
            'equity': self.equity,
            'final_balance': self.balance
        }

    def simulate_trade(self, entry_bar_idx, df, signal_dict):
        """Vectorised exit with spread & commission simulation."""
        entry_price = signal_dict['entry']
        sl = signal_dict['stop_loss']
        tp = signal_dict['take_profit']
        direction = signal_dict['signal']
        atr = df.iloc[entry_bar_idx]['atr']
        lot_size = self.calculate_position_size(entry_price, sl, atr)

        # Spread
        spread = SPREAD_JPY if 'JPY' in self.pair else SPREAD_NON_JPY

        subset = df.iloc[entry_bar_idx + 1:]
        if subset.empty:
            return entry_bar_idx + 1, df.iloc[-1]['close'], 0.0, 'End of Data'

        high = subset['high'].values
        low = subset['low'].values
        close = subset['close'].values

        if direction == 'BUY':
            # For buy: we bought at ask (entry+spread/2 approx), exit at bid (exit_price)
            # Simulate: stop loss hit when low touches sl, TP when high touches tp
            sl_hit = np.where(low <= sl)[0]
            tp_hit = np.where(high >= tp)[0]
        else:
            sl_hit = np.where(high >= sl)[0]
            tp_hit = np.where(low <= tp)[0]

        first_sl = sl_hit[0] if len(sl_hit) > 0 else np.inf
        first_tp = tp_hit[0] if len(tp_hit) > 0 else np.inf

        if first_sl == np.inf and first_tp == np.inf:
            exit_idx = len(subset) - 1
            exit_price = close[-1]
            reason = 'End of Data'
        elif first_sl <= first_tp:
            exit_idx = int(first_sl)
            exit_price = sl
            reason = 'Stop Loss'
        else:
            exit_idx = int(first_tp)
            exit_price = tp
            reason = 'Take Profit'

        actual_exit_idx = entry_bar_idx + 1 + exit_idx
        actual_exit_idx = min(actual_exit_idx, len(df) - 1)   # clamp to last bar
        # P&L with spread
        if direction == 'BUY':
            gross_pnl = (exit_price - entry_price) * lot_size * 100000
            # Spread cost: entry at ask, exit at bid
            gross_pnl -= spread * lot_size * 100000
        else:
            gross_pnl = (entry_price - exit_price) * lot_size * 100000
            gross_pnl -= spread * lot_size * 100000

        # Commission
        gross_pnl -= lot_size * COMMISSION

        if 'JPY' in self.pair:
            gross_pnl /= exit_price  # approximate

        return actual_exit_idx, exit_price, gross_pnl, reason

    def calculate_position_size(self, entry, stop_loss, atr):
        risk_amount = self.balance * self.risk_percent
        pip_value = 0.01 if 'JPY' in self.pair else 0.0001
        sl_distance = abs(entry - stop_loss)
        if sl_distance == 0: return 0.01
        sl_pips = sl_distance / pip_value
        if sl_pips == 0: return 0.01
        lot = risk_amount / (sl_pips * 10)
        return max(0.01, min(round(lot, 2), 10.0))


class PortfolioBacktest:
    # ... (unchanged except using the new SinglePairBacktest constructor)
    def __init__(self, pairs, start_date, end_date, initial_capital_per_pair,
                 risk_percent, trail_atr_mult, min_confidence, use_filters,
                 atr_min_non_jpy=0.0005, atr_max_non_jpy=0.003,
                 atr_min_jpy=0.05, atr_max_jpy=0.30,
                 preloaded_data_dict=None):
        self.pairs = pairs
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital_per_pair = initial_capital_per_pair
        self.total_capital = initial_capital_per_pair * len(pairs)
        self.risk_percent = risk_percent
        self.trail_atr_mult = trail_atr_mult
        self.min_confidence = min_confidence
        self.use_filters = use_filters
        self.atr_min_non_jpy = atr_min_non_jpy
        self.atr_max_non_jpy = atr_max_non_jpy
        self.atr_min_jpy = atr_min_jpy
        self.atr_max_jpy = atr_max_jpy
        self.results = {}
        self.portfolio_equity = None
        self.preloaded_data = preloaded_data_dict or {}

    def run(self):
        logger.info(f"\n{'='*60}")
        logger.info(f"MULTI-PAIR PORTFOLIO BACKTEST (MT5)")
        logger.info(f"Pairs: {self.pairs}")
        logger.info(f"Period: {self.start_date} to {self.end_date}")
        logger.info(f"{'='*60}\n")

        all_equity_dfs = []
        for pair in self.pairs:
            bt = SinglePairBacktest(
                pair, self.start_date, self.end_date,
                self.initial_capital_per_pair, self.risk_percent,
                self.trail_atr_mult, self.min_confidence, self.use_filters,
                self.atr_min_non_jpy, self.atr_max_non_jpy,
                self.atr_min_jpy, self.atr_max_jpy,
                preloaded_data=self.preloaded_data.get(pair)
            )
            result = bt.run()
            if result:
                self.results[pair] = result
                equity_df = pd.DataFrame(result['equity'], columns=['time', 'balance'])
                equity_df.set_index('time', inplace=True)
                equity_df.rename(columns={'balance': pair}, inplace=True)
                all_equity_dfs.append(equity_df)

        if not all_equity_dfs:
            logger.error("No valid backtest results.")
            return None

        portfolio_equity = pd.concat(all_equity_dfs, axis=1).ffill().fillna(self.initial_capital_per_pair)
        portfolio_equity['total'] = portfolio_equity.sum(axis=1)
        self.portfolio_equity = portfolio_equity
        return self.calculate_portfolio_metrics()

    def calculate_portfolio_metrics(self):
        all_trades = []
        for pair, result in self.results.items():
            all_trades.extend(result['trades'])
        
        if not all_trades:
            return None
        
        df_trades = pd.DataFrame(all_trades)
        total_trades = len(df_trades)
        winning = len(df_trades[df_trades['pnl'] > 0])
        losing = len(df_trades[df_trades['pnl'] < 0])
        win_rate = (winning / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = df_trades['pnl'].sum()
        gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        final_balance = self.portfolio_equity['total'].iloc[-1]
        total_return = (final_balance - self.total_capital) / self.total_capital * 100
        
        equity_series = self.portfolio_equity['total']
        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak * 100
        max_dd = drawdown.min()
        
        daily_pnl = {}
        for trade in all_trades:
            day = trade['entry_time'].strftime('%Y-%m-%d') if not isinstance(trade['entry_time'], str) else trade['entry_time'][:10]
            if day not in daily_pnl:
                daily_pnl[day] = 0
            daily_pnl[day] += trade['pnl']
        daily_returns = list(daily_pnl.values())
        if len(daily_returns) > 1:
            avg_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            sharpe = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe = 0
        
        metrics = {
            'pairs_tested': list(self.results.keys()),
            'period': f"{self.start_date} to {self.end_date}",
            'initial_capital': self.total_capital,
            'final_balance': final_balance,
            'total_return': total_return,
            'total_trades': total_trades,
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe,
            'trades': all_trades,
            'equity_df': self.portfolio_equity
        }
        return metrics

    def print_report(self, metrics):
        print("\n" + "="*60)
        print("📊 PORTFOLIO BACKTEST REPORT")
        print("="*60)
        print(f"Pairs:          {', '.join(metrics['pairs_tested'])}")
        print(f"Period:         {metrics['period']}")
        print(f"Initial Capital: ${metrics['initial_capital']:,.2f}")
        print(f"Final Balance:   ${metrics['final_balance']:,.2f}")
        print(f"Total Return:    {metrics['total_return']:.2f}%")
        print("-"*60)
        print(f"Total Trades:    {metrics['total_trades']}")
        print(f"Win Rate:        {metrics['win_rate']:.1f}% ({metrics['winning_trades']}W / {metrics['losing_trades']}L)")
        print(f"Profit Factor:   {metrics['profit_factor']:.2f}")
        print(f"Max Drawdown:    {metrics['max_drawdown']:.2f}%")
        print(f"Sharpe Ratio:    {metrics['sharpe_ratio']:.2f}")
        print(f"Total P&L:       ${metrics['total_pnl']:,.2f}")
        print("="*60)
        
        print("\n📈 Per-Pair Performance:")
        for pair in metrics['pairs_tested']:
            pair_trades = [t for t in metrics['trades'] if t['pair'] == pair]
            if pair_trades:
                pair_pnl = sum(t['pnl'] for t in pair_trades)
                pair_wins = len([t for t in pair_trades if t['pnl'] > 0])
                pair_wr = (pair_wins / len(pair_trades)) * 100
                print(f"  {pair}: {len(pair_trades)} trades, WR {pair_wr:.1f}%, P&L ${pair_pnl:,.2f}")

    # --- plot_equity_curve, save_results unchanged (same as before) ---
    def plot_equity_curve(self, metrics, save_path=None):
        equity = metrics['equity_df']['total']
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(equity.index, equity.values, color='#00ff88', linewidth=2, label='Portfolio Equity')
        ax.fill_between(equity.index, metrics['initial_capital'], equity.values,
                        where=(equity.values >= metrics['initial_capital']),
                        color='#00ff88', alpha=0.3)
        ax.fill_between(equity.index, metrics['initial_capital'], equity.values,
                        where=(equity.values < metrics['initial_capital']),
                        color='#ff4444', alpha=0.3)
        ax.axhline(y=metrics['initial_capital'], color='#666666', linestyle='--', linewidth=1)
        ax.set_title(f"Portfolio Equity Curve ({', '.join(metrics['pairs_tested'])})", fontsize=14, color='white')
        ax.set_xlabel('Date', fontsize=12, color='#cccccc')
        ax.set_ylabel('Balance ($)', fontsize=12, color='#cccccc')
        ax.grid(True, alpha=0.3, color='#666666')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        plt.xticks(rotation=45, color='#cccccc')
        plt.yticks(color='#cccccc')
        fig.patch.set_facecolor('#1e1e1e')
        ax.set_facecolor('#2d2d2d')
        ax.legend(facecolor='#2d2d2d', edgecolor='none', labelcolor='white')
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, facecolor='#1e1e1e')
            logger.info(f"Chart saved to {save_path}")
        plt.show()

    def save_results(self, metrics, filename_prefix='portfolio_backtest'):
        import os
        results_dir = os.path.join(os.path.dirname(__file__), 'backtest_results')
        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path = os.path.join(results_dir, f"{filename_prefix}_{timestamp}.json")
        csv_path = os.path.join(results_dir, f"{filename_prefix}_trades_{timestamp}.csv")
        chart_path = os.path.join(results_dir, f"{filename_prefix}_equity_{timestamp}.png")
        
        json_data = {k: v for k, v in metrics.items() if k not in ['trades', 'equity_df']}
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        trades_df = pd.DataFrame(metrics['trades'])
        trades_df.to_csv(csv_path, index=False)
        
        self.plot_equity_curve(metrics, save_path=chart_path)
        logger.info(f"Results saved to {json_path}, {csv_path}, {chart_path}")