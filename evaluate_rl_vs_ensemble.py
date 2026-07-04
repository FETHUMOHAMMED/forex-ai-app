"""
Compare RL Agent vs ML/ICT Ensemble on the same tick data.
Uses the best parameters from config.json and the trained PPO model.
"""

import os, sys, json, time
import numpy as np
import pandas as pd
from stable_baselines3 import PPO
from rl_env import ForexTradingEnv
from real_ai_service import RealAITrader

# ---------- CONFIG ----------
PAIR = 'EURUSD'
DATA_PATH = f"data/{PAIR}_ticks.csv"
MODEL_PATH = f"models/{PAIR}_ppo_trader.zip"
CONFIG_PATH = "config.json"

# Load best parameters
with open(CONFIG_PATH) as f:
    config = json.load(f)
best = {
    'min_confidence': config.get('min_confidence', 0.60),
    'risk_percent': config.get('risk_percent', 0.5),
    'atr_min_non_jpy': config.get('atr_min_non_jpy', 0.0007),
    'atr_max_non_jpy': config.get('atr_max_non_jpy', 0.0035),
    'atr_min_jpy': config.get('atr_min_jpy', 0.05),
    'atr_max_jpy': config.get('atr_max_jpy', 0.35),
}

# ---------- Data preparation ----------
print("📂 Loading tick data...")
ticks = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
ticks['mid'] = (ticks['bid'] + ticks['ask']) / 2
ohlc = ticks['mid'].resample('1min').ohlc()
ohlc.columns = ['open','high','low','close']
ohlc['volume'] = ticks['volume'].resample('1min').sum()
ohlc = ohlc.dropna()

ai = RealAITrader()
ohlc = ai.add_indicators(ohlc)

# Precompute ML signals for ensemble
print("🧠 Precomputing ML signals for ensemble...")
model = ai.models.get(PAIR)
if model is not None:
    feature_cols = [
        'rsi','macd','macd_signal','atr','volume_ratio',
        'bb_upper','bb_lower','fvg_buy','fvg_sell',
        'ob_buy','ob_sell','returns','high_low_ratio',
        'bb_buy','bb_sell','lv_buy','lv_sell','mss_buy','mss_sell'
    ]
    X = ohlc[feature_cols].fillna(0).values
    preds = model.predict(X)
    probs = model.predict_proba(X)
    ohlc['ml_signal'] = preds
    ohlc['ml_confidence'] = np.where(preds==1, probs[:,1], probs[:,0])
else:
    ohlc['ml_signal'] = 0
    ohlc['ml_confidence'] = 0.5

# Convert to arrays for fast ensemble loop
close_arr = ohlc['close'].values
atr_arr  = ohlc['atr'].values
ml_sig   = ohlc['ml_signal'].values.astype(int)
ml_conf  = ohlc['ml_confidence'].values
ict_buy  = (ohlc['fvg_buy'] | ohlc['ob_buy'] | ohlc['bb_buy'] | ohlc['lv_buy'] | ohlc['mss_buy']).values.astype(bool)
ict_sell = (ohlc['fvg_sell'] | ohlc['ob_sell'] | ohlc['bb_sell'] | ohlc['lv_sell'] | ohlc['mss_sell']).values.astype(bool)

# ---------- Ensemble Backtest ----------
def sim_trade(df, entry_idx, signal, sl, tp, lot):
    entry_price = df.iloc[entry_idx]['close']
    spread = 0.0002
    if signal == 'BUY': entry_price += spread
    else: entry_price -= spread
    subset = df.iloc[entry_idx+1:]
    if subset.empty: return len(df)-1, df.iloc[-1]['close'], 0.0
    h,l,c = subset['high'].values, subset['low'].values, subset['close'].values
    sl_hit = np.where(l <= sl)[0] if signal=='BUY' else np.where(h >= sl)[0]
    tp_hit = np.where(h >= tp)[0] if signal=='BUY' else np.where(l <= tp)[0]
    f_sl = sl_hit[0] if len(sl_hit) else np.inf
    f_tp = tp_hit[0] if len(tp_hit) else np.inf
    if f_sl==np.inf and f_tp==np.inf:
        ei, ep = len(subset)-1, c[-1]
    elif f_sl <= f_tp:
        ei, ep = int(f_sl), sl
    else:
        ei, ep = int(f_tp), tp
    actual = entry_idx + 1 + ei
    actual = min(actual, len(df)-1)
    pnl = (ep-entry_price)*lot*100000 if signal=='BUY' else (entry_price-ep)*lot*100000
    pnl -= lot*7.0   # commission
    return actual, ep, pnl

def calc_lot(balance, entry, sl, risk_pct):
    risk = balance * (risk_pct/100)
    sl_dist = abs(entry-sl)
    if sl_dist == 0: return 0.01
    lot = risk / (sl_dist/0.0001 * 10)
    return max(0.01, min(round(lot,2), 10.0))

print("🔄 Running ensemble backtest...")
balance_ens = 10000
all_pnl_ens = []
i = 100
while i < len(ohlc)-1:
    a = atr_arr[i]
    if pd.isna(a) or a < best['atr_min_non_jpy'] or a > best['atr_max_non_jpy']:
        i += 1; continue
    if ict_buy[i] and ml_sig[i]==1 and ml_conf[i]>0.55:
        signal, conf = 'BUY', ml_conf[i]
    elif ict_sell[i] and ml_sig[i]==0 and ml_conf[i]>0.55:
        signal, conf = 'SELL', ml_conf[i]
    elif ml_conf[i] > 0.65:
        signal, conf = ('BUY' if ml_sig[i]==1 else 'SELL'), ml_conf[i]
    elif ict_buy[i] and ml_conf[i]>0.51:
        signal, conf = 'BUY', 0.55
    elif ict_sell[i] and ml_conf[i]>0.51:
        signal, conf = 'SELL', 0.55
    elif ml_conf[i] > 0.51:
        signal, conf = ('BUY' if ml_sig[i]==1 else 'SELL'), ml_conf[i]
    else:
        i += 1; continue
    if conf < best['min_confidence']:
        i += 1; continue

    entry = close_arr[i]
    sl = entry - a*1.5 if signal=='BUY' else entry + a*1.5
    tp = entry + a*2.5 if signal=='BUY' else entry - a*2.5
    lot = calc_lot(balance_ens, entry, sl, best['risk_percent'])
    ei, ep, pnl = sim_trade(ohlc, i, signal, sl, tp, lot)
    balance_ens += pnl
    all_pnl_ens.append(pnl)
    i = ei + 1

# ---------- RL Agent Backtest ----------
print("🤖 Running RL agent on same data...")
env = ForexTradingEnv(ohlc, initial_balance=10000, risk_percent=best['risk_percent'],
                      atr_min=best['atr_min_non_jpy'], atr_max=best['atr_max_non_jpy'])
model_rl = PPO.load(MODEL_PATH)
obs, _ = env.reset()
done = False
all_pnl_rl = []
while not done:
    action, _ = model_rl.predict(obs, deterministic=True)
    obs, reward, done, trunc, info = env.step(action)
    if action == 3:   # close trade -> realized pnl
        all_pnl_rl.append(env.total_pnl - sum(all_pnl_rl))   # approximate last trade pnl
balance_rl = env.balance

# ---------- Print Comparison ----------
def metrics(pnls, balance):
    arr = np.array(pnls)
    if len(arr)==0: return {'P&L':0,'WR':0,'PF':0,'Trades':0}
    wins = np.sum(arr>0)
    total = len(arr)
    tot = arr.sum()
    gp = arr[arr>0].sum()
    gl = abs(arr[arr<0].sum())
    pf = gp/gl if gl else float('inf')
    wr = wins/total*100
    return {'P&L':tot, 'WR':wr, 'PF':pf, 'Trades':total}

ens = metrics(all_pnl_ens, balance_ens)
rl  = metrics(all_pnl_rl, balance_rl)

print("\n" + "="*50)
print("📊 RL vs Ensemble Comparison")
print("="*50)
print(f"{'Metric':<15} {'Ensemble':>12} {'RL Agent':>12}")
print("-"*50)
print(f"{'Total P&L':<15} ${ens['P&L']:>10.2f} ${rl['P&L']:>10.2f}")
print(f"{'Win Rate':<15} {ens['WR']:>10.1f}% {rl['WR']:>10.1f}%")
print(f"{'Profit Factor':<15} {ens['PF']:>10.2f} {rl['PF']:>10.2f}")
print(f"{'Trades':<15} {ens['Trades']:>10} {rl['Trades']:>10}")
print("-"*50)
if rl['P&L'] > ens['P&L']:
    print("🏆 RL Agent outperforms the Ensemble!")
elif ens['P&L'] > rl['P&L']:
    print("🏆 Ensemble outperforms the RL Agent!")
else:
    print("🤝 Both strategies are tied.")