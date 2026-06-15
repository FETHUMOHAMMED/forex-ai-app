"""
ULTRAFAST TICK BACKTEST – Resampled to 1‑Minute OHLC
Finishes 25 combinations in seconds.
"""

import os, sys, time, itertools
import numpy as np
import pandas as pd
from datetime import datetime

# ---------- CONFIG ----------
PAIRS = ['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NZDUSD','USDSGD']
INITIAL_CAPITAL = 2000
SPREAD_NON_JPY = 1.5   # pips
SPREAD_JPY    = 1.5

PARAM_GRID = {
    'risk_percent': [0.5, 1.0, 1.5, 2.0],
    'ema_fast': [20, 50],
    'ema_slow': [100, 200],
    'sl_atr_mult': [1.5, 2.0],
    'tp_atr_mult': [3.0, 4.0]
}
LIMIT_COMBOS = 25

def load_tick_csv(pair):
    path = f"data/{pair}_ticks.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df

def resample_to_min(tick_df):
    """Resample ticks to 1‑minute OHLC using the mid price."""
    tick_df['mid'] = (tick_df['bid'] + tick_df['ask']) / 2
    ohlc = tick_df['mid'].resample('1min').ohlc()
    ohlc.columns = ['open','high','low','close']
    ohlc['volume'] = tick_df['volume'].resample('1min').sum()
    ohlc.dropna(inplace=True)
    return ohlc

def simulate_trade_min(df, entry_idx, signal, sl, tp, lot, pair):
    """Fast vectorized exit on 1‑minute OHLC data."""
    spread_mult = 0.01 if 'JPY' in pair else 0.0001
    spread_price = SPREAD_JPY * spread_mult if 'JPY' in pair else SPREAD_NON_JPY * spread_mult
    entry_price = df.iloc[entry_idx]['close']
    if signal == 'BUY': entry_price += spread_price
    else: entry_price -= spread_price

    subset = df.iloc[entry_idx + 1:]
    if subset.empty:
        return len(df)-1, df.iloc[-1]['close'], 0.0, 'End'

    high = subset['high'].values
    low  = subset['low'].values
    close = subset['close'].values

    if signal == 'BUY':
        sl_hit = np.where(low <= sl)[0]
        tp_hit = np.where(high >= tp)[0]
    else:
        sl_hit = np.where(high >= sl)[0]
        tp_hit = np.where(low <= tp)[0]

    first_sl = sl_hit[0] if len(sl_hit) else np.inf
    first_tp = tp_hit[0] if len(tp_hit) else np.inf

    if first_sl == np.inf and first_tp == np.inf:
        exit_idx = len(subset)-1; exit_price = close[-1]; reason = 'End'
    elif first_sl <= first_tp:
        exit_idx = int(first_sl); exit_price = sl; reason = 'SL'
    else:
        exit_idx = int(first_tp); exit_price = tp; reason = 'TP'

    actual = entry_idx + 1 + exit_idx
    actual = min(actual, len(df)-1)

    if signal == 'BUY':
        pnl = (exit_price - entry_price) * lot * 100000
    else:
        pnl = (entry_price - exit_price) * lot * 100000
    if 'JPY' in pair: pnl /= exit_price
    return actual, exit_price, pnl, reason

def calc_lot(balance, entry, sl, risk_percent, pair):
    risk_amount = balance * (risk_percent / 100.0)
    sl_dist = abs(entry - sl)
    if sl_dist == 0: return 0.01
    pip_value = 0.01 if 'JPY' in pair else 0.0001
    sl_pips = sl_dist / pip_value
    if sl_pips == 0: return 0.01
    lot = risk_amount / (sl_pips * 10)
    return max(0.01, min(round(lot,2), 10.0))

def gen_combos(grid, limit):
    keys = list(grid.keys())
    vals = list(grid.values())
    combos = list(itertools.product(*vals))
    if limit and len(combos) > limit:
        step = max(1, len(combos)//limit)
        combos = combos[::step][:limit]
    return [dict(zip(keys, c)) for c in combos]

def main():
    print("="*60)
    print("⚡ ULTRAFAST TICK BACKTEST (1‑Minute Resample)")
    print("="*60)

    # Load and resample all pairs
    cached = {}
    for pair in PAIRS:
        print(f"📂 Loading & resampling {pair} …")
        tick_df = load_tick_csv(pair)
        if tick_df is None or len(tick_df) == 0:
            print(f"   ❌ No tick CSV for {pair}")
            continue
        ohlc = resample_to_min(tick_df)
        if len(ohlc) < 100:
            print(f"   ❌ Not enough data for {pair}")
            continue
        cached[pair] = ohlc
        print(f"   ✅ {pair} – {len(ohlc)} 1‑min bars")

    if not cached:
        print("No data."); sys.exit(1)

    combos = gen_combos(PARAM_GRID, LIMIT_COMBOS)
    print(f"\n🚀 Testing {len(combos)} combinations …\n")
    results = []

    for idx, params in enumerate(combos, 1):
        t0 = time.time()
        all_trades = []
        for pair, df in cached.items():
            atr = (df['high'] - df['low']).rolling(14).mean()
            ema_fast = df['close'].ewm(span=params['ema_fast'], adjust=False).mean()
            ema_slow = df['close'].ewm(span=params['ema_slow'], adjust=False).mean()
            cross_above = (ema_fast > ema_slow) & (ema_fast.shift() <= ema_slow.shift())
            cross_below = (ema_fast < ema_slow) & (ema_fast.shift() >= ema_slow.shift())

            balance = INITIAL_CAPITAL
            # Get list of entry indices
            entries = np.where(cross_above | cross_below)[0]
            for i in entries:
                if i < params['ema_slow']:
                    continue
                signal = 'BUY' if cross_above.iloc[i] else 'SELL'
                entry = df.iloc[i]['close']
                atr_val = atr.iloc[i]
                if pd.isna(atr_val) or atr_val == 0:
                    continue
                sl_mult = params['sl_atr_mult']
                tp_mult = params['tp_atr_mult']
                if signal == 'BUY':
                    sl = entry - atr_val * sl_mult
                    tp = entry + atr_val * tp_mult
                else:
                    sl = entry + atr_val * sl_mult
                    tp = entry - atr_val * tp_mult

                lot = calc_lot(balance, entry, sl, params['risk_percent'], pair)
                ei, ep, pnl, _ = simulate_trade_min(df, i, signal, sl, tp, lot, pair)
                balance += pnl
                all_trades.append(pnl)

        elapsed = time.time() - t0
        if all_trades:
            arr = np.array(all_trades)
            wins = np.sum(arr > 0)
            total = len(arr)
            total_pnl = arr.sum()
            gross_profit = arr[arr > 0].sum()
            gross_loss = abs(arr[arr < 0].sum())
            pf = gross_profit / gross_loss if gross_loss else float('inf')
            wr = wins / total * 100 if total else 0
            score = pf * (wr / 100)
            results.append({**params, 'score': score, 'total_pnl': total_pnl,
                            'win_rate': wr, 'profit_factor': pf, 'trades': total})
            print(f"[{idx:2d}/{len(combos)}] fast={params['ema_fast']} slow={params['ema_slow']} "
                  f"risk={params['risk_percent']:.1f}% → PnL ${total_pnl:.0f} "
                  f"WR {wr:.1f}% PF {pf:.2f} score {score:.4f} ⏱️{elapsed:.1f}s")
        else:
            print(f"[{idx:2d}/{len(combos)}] no trades ⏱️{elapsed:.1f}s")

    if results:
        df_res = pd.DataFrame(results).sort_values('score', ascending=False)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = f"tick_optimization_{ts}.csv"
        df_res.to_csv(csv_path, index=False)
        print(f"\n✅ Results saved to {csv_path}")
        print("\n🏆 TOP 5 PARAMETER SETS")
        for i, (_, row) in enumerate(df_res.head(5).iterrows()):
            print(f"#{i+1} Score {row['score']:.4f} | fast={row['ema_fast']} slow={row['ema_slow']} "
                  f"risk={row['risk_percent']:.1f}% | PnL ${row['total_pnl']:.0f} WR {row['win_rate']:.1f}% PF {row['profit_factor']:.2f}")
    else:
        print("❌ No successful combinations.")

if __name__ == "__main__":
    main()