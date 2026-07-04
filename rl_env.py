"""
rl_env.py – Enhanced Forex trading environment for RL.
Provides mark-to-market reward at every step to encourage active trading.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd

class ForexTradingEnv(gym.Env):
    metadata = {'render_modes': ['human']}

    def __init__(self, df, initial_balance=10000, spread=0.0002, commission=7.0,
                 window_size=20, risk_percent=0.5, atr_min=0.0005, atr_max=0.003,
                 atr_min_jpy=0.05, atr_max_jpy=0.3,
                 idle_penalty_per_step=0.001, profit_scaling=100):
        super().__init__()

        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.spread = spread
        self.commission = commission
        self.window_size = window_size
        self.risk_percent = risk_percent / 100.0
        self.atr_min = atr_min
        self.atr_max = atr_max
        self.atr_min_jpy = atr_min_jpy
        self.atr_max_jpy = atr_max_jpy
        self.idle_penalty = idle_penalty_per_step   # NEW
        self.profit_scaling = profit_scaling        # NEW

        self.feature_cols = [
            'rsi', 'macd', 'macd_signal', 'atr', 'volume_ratio',
            'bb_upper', 'bb_lower', 'fvg_buy', 'fvg_sell',
            'ob_buy', 'ob_sell', 'returns', 'high_low_ratio'
        ]

        obs_dim = window_size * (len(self.feature_cols) + 1) + 5   # +5 for account info
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32)
        self.action_space = spaces.Discrete(4)   # 0=Hold, 1=Buy, 2=Sell, 3=Close
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.inventory = 0.0
        self.entry_price = 0.0
        self.position_type = 0
        self.total_pnl = 0.0
        self.unrealised_pnl = 0.0
        return self._get_obs(), {}

    def _get_obs(self):
        start = self.current_step - self.window_size
        end = self.current_step
        window = self.df.iloc[start:end][self.feature_cols].values.astype(np.float32)
        prices = self.df.iloc[start:end]['close'].values.astype(np.float32).reshape(-1, 1)
        combined = np.concatenate([prices, window], axis=1).flatten()

        # account info: balance, inventory, position_type, unrealised_pnl, total_pnl
        account_info = np.array([self.balance, self.inventory, self.position_type,
                                 self.unrealised_pnl, self.total_pnl], dtype=np.float32)
        return np.concatenate([combined, account_info])

    def step(self, action):
        row = self.df.iloc[self.current_step]
        price = row['close']
        atr = row['atr'] if not pd.isna(row['atr']) else price * 0.0015

        reward = 0.0
        done = False
        trunc = False

        # ----- Execute action -----
        if action == 1 and self.position_type == 0:   # BUY
            self.entry_price = price + self.spread
            lot = self._calc_lot(self.balance, self.entry_price, self.entry_price - atr*1.5)
            self.inventory = lot * 100000
            self.position_type = 1
            self.balance -= lot * self.commission
        elif action == 2 and self.position_type == 0: # SELL
            self.entry_price = price - self.spread
            lot = self._calc_lot(self.balance, self.entry_price, self.entry_price + atr*1.5)
            self.inventory = -lot * 100000
            self.position_type = -1
            self.balance -= lot * self.commission
        elif action == 3 and self.position_type != 0: # CLOSE
            exit_price = price - self.spread if self.position_type == 1 else price + self.spread
            pnl = (exit_price - self.entry_price) * self.inventory if self.position_type == 1 else (self.entry_price - exit_price) * abs(self.inventory)
            self.balance += pnl
            self.total_pnl += pnl
            reward += pnl * self.profit_scaling   # big reward for closing
            self.inventory = 0.0
            self.position_type = 0
            self.entry_price = 0.0
            self.unrealised_pnl = 0.0

        # ----- Mark‑to‑market reward (every step) -----
        elif self.position_type != 0:
            # Calculate current unrealised PnL
            if self.position_type == 1:
                unrealised = (price - self.entry_price) * self.inventory
            else:
                unrealised = (self.entry_price - price) * abs(self.inventory)
            reward += (unrealised - self.unrealised_pnl) * self.profit_scaling   # delta mtm
            self.unrealised_pnl = unrealised

        # ----- Idle penalty -----
        if self.position_type == 0:
            reward -= self.idle_penalty

        self.current_step += 1
        if self.current_step >= len(self.df) - 1:
            # Force close at end
            if self.position_type != 0:
                exit_price = self.df.iloc[-1]['close']
                pnl = (exit_price - self.entry_price) * self.inventory if self.position_type == 1 else (self.entry_price - exit_price) * abs(self.inventory)
                self.balance += pnl
                self.total_pnl += pnl
                reward += pnl * self.profit_scaling
            done = True
            trunc = True

        return self._get_obs(), reward, done, trunc, {}

    def _calc_lot(self, balance, entry, sl):
        risk_amount = balance * self.risk_percent
        sl_dist = abs(entry - sl)
        if sl_dist == 0:
            return 0.01
        lot = risk_amount / (sl_dist / 0.0001 * 10)
        return max(0.01, min(round(lot, 2), 10.0))