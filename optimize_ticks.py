"""
optimize_ticks.py – Tick‑level parameter optimization.
Resamples ticks to 1‑second OHLC for realistic intra‑bar execution.
"""

import os, sys, time, itertools
import numpy as np
import pandas as pd
from datetime import datetime

# ---------- CONFIG ----------
PAIRS = ['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NZDUSD','USDSGD']
INITIAL_CAPITAL = 2000
SPREAD_NON_JPY = 0.0002
SPREAD_JPY    = 0.02
COMMISSION    = 7.0

PARAM_GRID = {
    'min_confidence': [0.50, 0.55, 0.60, 0.65],
    'risk_percent': [0.5, 1.0, 1.5, 2.0],
    'atr_min_non_jpy': [0.0002, 0.0003, 0.0005, 0.0007],
    'atr_max_non_jpy': [0.0025, 0.0030, 0.0035, 0.0040],
    'atr_min_jpy': [0.03, 0.04, 0.05, 0.06],
    'atr_max_jpy': [0.25, 0.30, 0.35, 0.40]
}
LIMIT_COMBOS = 25

def load_tick_data(pair):
    """Load tick CSV and resample to 1‑second OHLC."""
    path = f"data/{pair}_ticks.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    # Resample to 1‑second candles (realistic execution)
    ohlc = df['bid'].resample('1s').ohlc()
    ohlc['volume'] = df['volume'].resample('1s').sum()
    ohlc.columns = ['open','high','low','close','volume']
    ohlc.dropna(inplace=True)
    return ohlc

def simulate_tick_trade(df, entry_idx, signal, sl, tp, lot, pair):
    """Vectorized trade exit on 1‑second data."""
    spread = SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY
    entry_price = df.iloc[entry_idx]['close']
    if signal == 'BUY': entry_price += spread
    else: entry_price -= spread

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

    actual = min(entry_idx + 1 + exit_idx, len(df)-1)

    if signal == 'BUY':
        pnl = (exit_price - entry_price) * lot * 100000
        pnl -= spread * lot * 100000
    else:
        pnl = (entry_price - exit_price) * lot * 100000
        pnl -= spread * lot * 100000
    pnl -= lot * COMMISSION
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
        step = len(combos) // limit
        combos = combos[::step][:limit]
    return [dict(zip(keys, c)) for c in combos]

def main():
    print("="*60)
    print("🔧 TICK‑LEVEL PARAMETER OPTIMISATION")
    print("="*60)

    # Load all tick data
    cached = {}
    for pair in PAIRS:
        print(f"📂 Loading {pair} ticks …")
        df = load_tick_data(pair)
        if df is not None and len(df) > 100:
            cached[pair] = df
            print(f"   ✅ {pair} – {len(df)} 1‑sec bars")
        else:
            print(f"   ❌ {pair} – skipped")

    if not cached:
        print("No tick data."); sys.exit(1)

    combos = gen_combos(PARAM_GRID, LIMIT_COMBOS)
    print(f"\n🚀 Testing {len(combos)} combinations on 1‑second data …\n")
    results = []

    for idx, params in enumerate(combos, 1):
        t0 = time.time()
        all_trades = []
        # For tick data we use a simple momentum signal (no ML needed for the demo)
        for pair, df in cached.items():
            balance = INITIAL_CAPITAL
            # Compute fast/slow EMA on the 1‑sec data
            ema_fast = df['close'].ewm(span=20).mean()
            ema_slow = df['close'].ewm(span=50).mean()
            for i in range(1, len(df)):
                if i < 50: continue
                if ema_fast.iloc[i] > ema_slow.iloc[i] and ema_fast.iloc[i-1] <= ema_slow.iloc[i-1]:
                    signal = 'BUY'
                elif ema_fast.iloc[i] < ema_slow.iloc[i] and ema_fast.iloc[i-1] >= ema_slow.iloc[i-1]:
                    signal = 'SELL'
                else:
                    continue

                entry = df.iloc[i]['close']
                atr = (df['high'] - df['low']).rolling(14).mean().iloc[i]
                sl_mult, tp_mult = 2.0, 3.0
                if signal == 'BUY':
                    sl = entry - atr * sl_mult
                    tp = entry + atr * tp_mult
                else:
                    sl = entry + atr * sl_mult
                    tp = entry - atr * tp_mult

                lot = calc_lot(balance, entry, sl, params['risk_percent'], pair)
                ei, ep, pnl, _ = simulate_tick_trade(df, i, signal, sl, tp, lot, pair)
                balance += pnl
                all_trades.append(pnl)
                i = ei + 1

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
            print(f"[{idx:2d}/{len(combos)}] risk{params['risk_percent']:.1f}% → PnL ${total_pnl:.0f} "
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
            print(f"#{i+1} Score {row['score']:.4f} | Risk {row['risk_percent']:.1f}% | "
                  f"PnL ${row['total_pnl']:.0f} WR {row['win_rate']:.1f}% PF {row['profit_factor']:.2f}")
    else:
        print("❌ No successful combinations.")

if __name__ == "__main__":
    main()