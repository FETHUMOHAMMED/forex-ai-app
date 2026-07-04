import numpy as np
import pandas as pd

class BacktestEngine:
    def __init__(self, ai_trader, execution_engine):
        self.ai = ai_trader
        self.exec = execution_engine

    def run(self, df, pair, initial_balance=2000, risk_percent=1.0,
            min_confidence=0.55, use_filters=True,
            atr_min=0.0005, atr_max=0.003, atr_min_jpy=0.05, atr_max_jpy=0.3):
        df = self.ai.add_indicators(df)
        if df is None or len(df) < 100:
            return []

        balance = initial_balance
        trades = []
        position = None

        for i in range(100, len(df)-1):
            if position is not None:
                continue  # Only one trade at a time for simplicity

            row = df.iloc[i]
            signal_data = self.ai.get_signal_from_row(row, pair, use_filters=use_filters,
                                                      atr_min=atr_min, atr_max=atr_max,
                                                      atr_min_jpy=atr_min_jpy, atr_max_jpy=atr_max_jpy)
            if not signal_data or signal_data['confidence'] < min_confidence:
                continue

            # Optional trend filter
            if use_filters and i >= 50:
                ema_slice = df['close'].iloc[i-49:i+1]
                trend = 'BULLISH' if ema_slice.iloc[-1] > ema_slice.iloc[0] else 'BEARISH'
                if (signal_data['signal'] == 'BUY' and trend == 'BEARISH') or \
                   (signal_data['signal'] == 'SELL' and trend == 'BULLISH'):
                    continue

            entry = signal_data['entry']
            sl = signal_data['stop_loss']
            tp = signal_data['take_profit']
            signal = signal_data['signal']
            lot_size = self.calculate_lot(balance, entry, sl, risk_percent)

            exit_idx, exit_price, pnl, reason = self.exec.simulate_trade(
                df, i, signal, sl, tp, lot_size, pair
            )

            balance += pnl
            trades.append({
                'pair': pair,
                'entry_time': df.index[i],
                'exit_time': df.index[exit_idx],
                'signal': signal,
                'entry': entry,
                'exit': exit_price,
                'pnl': pnl,
                'reason': reason,
                'balance': balance
            })

        return trades

    def calculate_lot(self, balance, entry, sl, risk_percent):
        risk_amount = balance * (risk_percent / 100.0)
        pip_value = 0.01  # for JPY? we'll handle generically
        # This is simplified – your existing calc is fine. We'll reuse it.
        # For now, a safe calculation:
        sl_distance = abs(entry - sl)
        if sl_distance == 0:
            return 0.01
        pip = sl_distance / 0.0001  # approximate for non-JPY
        lot = risk_amount / (pip * 10)
        return max(0.01, min(round(lot, 2), 10.0))