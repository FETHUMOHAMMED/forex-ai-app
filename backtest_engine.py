"""
BACKTESTING ENGINE FOR FOREX AI TRADING SYSTEM
Replays historical MT5 data and simulates trades using the same logic as live.
"""

import os
import sys
import json
import warnings
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

# Import the AI trader (reuse signal logic)
from real_ai_service import RealAITrader

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class BacktestEngine:
    def __init__(self, pair='EURUSD', start_date='2024-01-01', end_date='2024-12-31',
                 initial_balance=10000, risk_percent=1.0, trail_atr_mult=1.0,
                 min_confidence=0.55, use_filters=True):
        """
        Initialize backtest parameters.
        """
        self.pair = pair
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.initial_balance = initial_balance
        self.risk_percent = risk_percent / 100.0  # Convert to decimal
        self.trail_atr_mult = trail_atr_mult
        self.min_confidence = min_confidence
        self.use_filters = use_filters   # Apply trend & volatility filters
        
        # AI trader for signal generation
        self.ai = RealAITrader()
        # We'll override fetch_data to use our historical data
        
        # Performance tracking
        self.trades = []
        self.equity_curve = []
        self.balance = initial_balance
        self.open_position = None  # Only one position at a time for simplicity
        
        # Connect to MT5
        if not mt5.initialize():
            logger.error("MT5 init failed")
            sys.exit(1)
        logger.info("✅ MT5 connected for backtesting")

    def fetch_historical_data(self):
        """Download historical bars from MT5 for the specified period."""
        symbol = self.ai._get_mt5_symbol(self.pair)
        if not symbol:
            logger.error(f"Symbol not found for {self.pair}")
            return None
        
        # Convert dates to MT5 format
        start = self.start_date
        end = self.end_date
        
        # Get all available bars in date range
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start, end)
        if rates is None or len(rates) == 0:
            logger.error(f"No historical data for {self.pair}")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.columns = ['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
        df['volume'] = df['tick_volume']
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        logger.info(f"Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
        return df

    def calculate_position_size(self, entry, stop_loss, atr):
        """Calculate lot size based on risk percent (same as live)."""
        risk_amount = self.balance * self.risk_percent
        
        if 'JPY' in self.pair:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        sl_distance = abs(entry - stop_loss)
        if sl_distance == 0:
            return 0.01
        
        sl_pips = sl_distance / pip_value
        if sl_pips == 0:
            return 0.01
        
        lot_size = risk_amount / (sl_pips * 10)
        lot_size = round(lot_size, 2)
        lot_size = max(0.01, min(lot_size, 10.0))
        return lot_size

    def simulate_trade(self, signal, entry_bar_idx, df):
        """
        Simulate a trade from entry to exit (SL, TP, or trailing stop).
        Returns: exit_price, exit_time, pnl, exit_reason
        """
        entry_price = signal['entry']
        sl = signal['stop_loss']
        tp = signal['take_profit']
        direction = signal['signal']
        atr = df.iloc[entry_bar_idx]['atr']
        
        # Position size
        lot_size = self.calculate_position_size(entry_price, sl, atr)
        
        # Simulate bar-by-bar
        for i in range(entry_bar_idx + 1, len(df)):
            bar = df.iloc[i]
            
            if direction == 'BUY':
                # Check stop loss first (low touches SL)
                if bar['low'] <= sl:
                    exit_price = sl
                    exit_reason = 'Stop Loss'
                    pnl = (exit_price - entry_price) * lot_size * 100000
                    if 'JPY' in self.pair:
                        pnl = (exit_price - entry_price) * lot_size * 100000 / exit_price
                    return i, exit_price, pnl, exit_reason
                
                # Check take profit
                if bar['high'] >= tp:
                    exit_price = tp
                    exit_reason = 'Take Profit'
                    pnl = (exit_price - entry_price) * lot_size * 100000
                    if 'JPY' in self.pair:
                        pnl = (exit_price - entry_price) * lot_size * 100000 / exit_price
                    return i, exit_price, pnl, exit_reason
                
                # Trailing stop (optional)
                if self.trail_atr_mult > 0:
                    trail_distance = atr * self.trail_atr_mult
                    new_sl = bar['close'] - trail_distance
                    if new_sl > sl:
                        sl = new_sl
            else:  # SELL
                if bar['high'] >= sl:
                    exit_price = sl
                    exit_reason = 'Stop Loss'
                    pnl = (entry_price - exit_price) * lot_size * 100000
                    if 'JPY' in self.pair:
                        pnl = (entry_price - exit_price) * lot_size * 100000 / exit_price
                    return i, exit_price, pnl, exit_reason
                
                if bar['low'] <= tp:
                    exit_price = tp
                    exit_reason = 'Take Profit'
                    pnl = (entry_price - exit_price) * lot_size * 100000
                    if 'JPY' in self.pair:
                        pnl = (entry_price - exit_price) * lot_size * 100000 / exit_price
                    return i, exit_price, pnl, exit_reason
                
                if self.trail_atr_mult > 0:
                    trail_distance = atr * self.trail_atr_mult
                    new_sl = bar['close'] + trail_distance
                    if new_sl < sl:
                        sl = new_sl
        
        # If never hit, close at last bar
        last_bar = df.iloc[-1]
        exit_price = last_bar['close']
        exit_reason = 'End of Data'
        if direction == 'BUY':
            pnl = (exit_price - entry_price) * lot_size * 100000
            if 'JPY' in self.pair:
                pnl = pnl / exit_price
        else:
            pnl = (entry_price - exit_price) * lot_size * 100000
            if 'JPY' in self.pair:
                pnl = pnl / exit_price
        return len(df) - 1, exit_price, pnl, exit_reason

    def run(self):
        """Execute the backtest."""
        logger.info(f"\n{'='*60}")
        logger.info(f"BACKTEST: {self.pair} | {self.start_date.date()} to {self.end_date.date()}")
        logger.info(f"{'='*60}")
        
        df = self.fetch_historical_data()
        if df is None:
            return None
        
        # Add indicators
        df = self.ai.add_indicators(df)
        if df is None or len(df) < 100:
            logger.error("Insufficient data after indicators")
            return None
        
        # Reset state
        self.balance = self.initial_balance
        self.trades = []
        self.equity_curve = [{'time': df.index[0], 'balance': self.balance}]
        in_position = False
        entry_idx = 0
        
        logger.info(f"Processing {len(df)} bars...")
        
        for i in range(100, len(df)):  # Start after warmup
            if in_position:
                continue  # We'll handle exit in simulation
            
            # Generate signal for this bar (use latest data up to i)
            window_df = df.iloc[:i+1].copy()
            latest = window_df.iloc[-1]
            
            # Skip if insufficient data
            if pd.isna(latest['rsi']):
                continue
            
            # Apply volatility filter
            atr = latest['atr']
            if self.use_filters:
                if 'JPY' in self.pair:
                    if atr < 0.05 or atr > 0.30:
                        continue
                else:
                    if atr < 0.0005 or atr > 0.003:
                        continue
            
            # ICT signals
            ict_buy = bool(latest.get('fvg_buy', 0) or latest.get('ob_buy', 0) or
                           latest.get('bb_buy', 0) or latest.get('lv_buy', 0) or
                           latest.get('mss_buy', 0))
            ict_sell = bool(latest.get('fvg_sell', 0) or latest.get('ob_sell', 0) or
                            latest.get('bb_sell', 0) or latest.get('lv_sell', 0) or
                            latest.get('mss_sell', 0))
            
            # ML prediction
            model = self.ai.models.get(self.pair)
            ml_signal = None
            ml_conf = 0.5
            if model is not None:
                feature_cols = [
                    'rsi', 'macd', 'macd_signal', 'atr', 'volume_ratio',
                    'bb_upper', 'bb_lower', 'fvg_buy', 'fvg_sell',
                    'ob_buy', 'ob_sell', 'returns', 'high_low_ratio',
                    'bb_buy', 'bb_sell', 'lv_buy', 'lv_sell', 'mss_buy', 'mss_sell'
                ]
                try:
                    X = pd.DataFrame([latest[feature_cols].fillna(0).values], columns=feature_cols)
                    proba = model.predict_proba(X)[0]
                    pred = model.predict(X)[0]
                    ml_signal = 'BUY' if pred == 1 else 'SELL'
                    ml_conf = float(proba[1] if pred == 1 else proba[0])
                except:
                    pass
            
            # Ensemble signal (simplified version of real_ai_service)
            signal = None
            confidence = 0.5
            if ict_buy and ml_signal == 'BUY' and ml_conf > 0.55:
                signal = 'BUY'
                confidence = ml_conf
            elif ict_sell and ml_signal == 'SELL' and ml_conf > 0.55:
                signal = 'SELL'
                confidence = ml_conf
            elif ml_conf > 0.65:
                signal = ml_signal
                confidence = ml_conf
            elif ict_buy and ml_conf > 0.51:
                signal = 'BUY'
                confidence = 0.55
            elif ict_sell and ml_conf > 0.51:
                signal = 'SELL'
                confidence = 0.55
            elif ml_signal and ml_conf > 0.51:
                signal = ml_signal
                confidence = ml_conf
            
            if not signal or confidence < self.min_confidence:
                continue
            
            # Multi-timeframe filter (optional - skip for speed)
            if self.use_filters:
                # Quick H1 trend approximation using EMA on current data
                if len(window_df) >= 50:
                    window_df['ema50'] = window_df['close'].ewm(span=50).mean()
                    trend = 'BULLISH' if window_df['ema50'].iloc[-1] > window_df['ema50'].iloc[-10] else 'BEARISH'
                    if (signal == 'BUY' and trend == 'BEARISH') or (signal == 'SELL' and trend == 'BULLISH'):
                        continue
            
            # Entry
            entry_price = latest['close']
            sl_mult, tp_mult = 1.5, 2.5
            if signal == 'BUY':
                sl = entry_price - atr * sl_mult
                tp = entry_price + atr * tp_mult
            else:
                sl = entry_price + atr * sl_mult
                tp = entry_price - atr * tp_mult
            
            signal_dict = {
                'pair': self.pair,
                'signal': signal,
                'confidence': confidence,
                'entry': entry_price,
                'stop_loss': sl,
                'take_profit': tp
            }
            
            # Simulate trade
            exit_idx, exit_price, pnl, reason = self.simulate_trade(signal_dict, i, df)
            
            # Record trade
            trade = {
                'entry_time': df.index[i],
                'exit_time': df.index[exit_idx],
                'signal': signal,
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'reason': reason,
                'bars_held': exit_idx - i
            }
            self.trades.append(trade)
            self.balance += pnl
            self.equity_curve.append({'time': df.index[exit_idx], 'balance': self.balance})
            
            # Skip to exit index
            i = exit_idx
        
        # Calculate metrics
        return self.calculate_metrics()

    def calculate_metrics(self):
        """Compute performance statistics."""
        if not self.trades:
            logger.info("No trades executed.")
            return None
        
        df_trades = pd.DataFrame(self.trades)
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['pnl'] > 0])
        losing_trades = len(df_trades[df_trades['pnl'] < 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = df_trades['pnl'].sum()
        avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df_trades[df_trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # Profit factor
        gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        # Max drawdown
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['peak'] = equity_df['balance'].cummax()
        equity_df['drawdown'] = (equity_df['balance'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()
        
        # Sharpe ratio (simplified)
        returns = df_trades['pnl'] / self.initial_balance
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 24 * 4) if returns.std() > 0 else 0  # Annualized (15-min bars)
        
        metrics = {
            'pair': self.pair,
            'period': f"{self.start_date.date()} to {self.end_date.date()}",
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_return': (self.balance - self.initial_balance) / self.initial_balance * 100,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'trades': self.trades
        }
        
        return metrics

    def print_report(self, metrics):
        """Display formatted backtest report."""
        if not metrics:
            return
        
        print("\n" + "="*60)
        print("📊 BACKTEST REPORT")
        print("="*60)
        print(f"Pair:           {metrics['pair']}")
        print(f"Period:         {metrics['period']}")
        print(f"Initial:        ${metrics['initial_balance']:,.2f}")
        print(f"Final:          ${metrics['final_balance']:,.2f}")
        print(f"Return:         {metrics['total_return']:.2f}%")
        print("-"*60)
        print(f"Total Trades:   {metrics['total_trades']}")
        print(f"Win Rate:       {metrics['win_rate']:.1f}%")
        print(f"Profit Factor:  {metrics['profit_factor']:.2f}")
        print(f"Max Drawdown:   {metrics['max_drawdown']:.2f}%")
        print(f"Sharpe Ratio:   {metrics['sharpe_ratio']:.2f}")
        print(f"Avg Win:        ${metrics['avg_win']:,.2f}")
        print(f"Avg Loss:       ${metrics['avg_loss']:,.2f}")
        print(f"Total P&L:      ${metrics['total_pnl']:,.2f}")
        print("="*60)

    def save_results(self, metrics, filename=None):
        """Save backtest results to JSON and CSV."""
        if filename is None:
            filename = f"backtest_{self.pair}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save metrics as JSON
        json_data = {k: v for k, v in metrics.items() if k != 'trades'}
        json_data['trades'] = [{k: str(v) if isinstance(v, pd.Timestamp) else v 
                                for k, v in trade.items()} for trade in metrics['trades']]
        with open(f"{filename}.json", 'w') as f:
            json.dump(json_data, f, indent=2)
        
        # Save trades as CSV
        trades_df = pd.DataFrame(metrics['trades'])
        trades_df.to_csv(f"{filename}_trades.csv", index=False)
        logger.info(f"Results saved to {filename}.json and {filename}_trades.csv")

def main():
    # Example usage
    engine = BacktestEngine(
        pair='EURUSD',
        start_date='2025-01-01',
        end_date='2025-04-01',
        initial_balance=10000,
        risk_percent=1.0,
        trail_atr_mult=1.0,
        min_confidence=0.55,
        use_filters=True
    )
    
    metrics = engine.run()
    if metrics:
        engine.print_report(metrics)
        engine.save_results(metrics)

if __name__ == "__main__":
    main()