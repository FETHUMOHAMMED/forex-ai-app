import numpy as np

class ExecutionEngine:
    def __init__(self, spread_non_jpy=0.0002, spread_jpy=0.02, commission=7.0, slippage=0.00005):
        self.spread_non_jpy = spread_non_jpy
        self.spread_jpy = spread_jpy
        self.commission = commission
        self.slippage = slippage

    def simulate_trade(self, df, entry_idx, signal, sl, tp, lot_size, pair):
        entry_price = df.iloc[entry_idx]['close']
        spread = self.spread_jpy if 'JPY' in pair else self.spread_non_jpy

        # Apply spread + slippage at entry
        if signal == 'BUY':
            entry_price += spread + self.slippage
        else:
            entry_price -= spread + self.slippage

        for i in range(entry_idx + 1, len(df)):
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']

            if signal == 'BUY':
                if low <= sl:
                    exit_price = sl - self.slippage
                    reason = 'SL'
                    break
                if high >= tp:
                    exit_price = tp - self.slippage
                    reason = 'TP'
                    break
            else:
                if high >= sl:
                    exit_price = sl + self.slippage
                    reason = 'SL'
                    break
                if low <= tp:
                    exit_price = tp + self.slippage
                    reason = 'TP'
                    break
        else:
            exit_price = df.iloc[-1]['close']
            reason = 'EOD'

        # PnL
        if signal == 'BUY':
            pnl = (exit_price - entry_price)
        else:
            pnl = (entry_price - exit_price)

        pnl = pnl * lot_size * 100000
        pnl -= lot_size * self.commission

        # For JPY pairs the pip value is different; we already handle it by the lot calculation
        # If needed, adjust here, but this is a good approximation.
        return i, exit_price, pnl, reason