from rl_env import ForexTradingEnv
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import pandas as pd
import os

# ---------- CONFIG ----------
PAIR = 'EURUSD'
DATA_PATH = f"data/{PAIR}_ticks.csv"

from real_ai_service import RealAITrader
ai = RealAITrader()

ticks = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
ticks['mid'] = (ticks['bid'] + ticks['ask']) / 2
ohlc = ticks['mid'].resample('1min').ohlc()
ohlc.columns = ['open','high','low','close']
ohlc['volume'] = ticks['volume'].resample('1min').sum()
ohlc = ohlc.dropna()
ohlc = ai.add_indicators(ohlc)

env = DummyVecEnv([lambda: ForexTradingEnv(ohlc)])

model = PPO('MlpPolicy', env, verbose=1, learning_rate=0.0003, n_steps=2048,
            batch_size=64, n_epochs=10, gamma=0.99, gae_lambda=0.95,
            clip_range=0.2, ent_coef=0.01)
model.learn(total_timesteps=100_000)

os.makedirs('models', exist_ok=True)
model.save(f"models/{PAIR}_ppo_trader")
print(f"✅ RL model saved for {PAIR}")