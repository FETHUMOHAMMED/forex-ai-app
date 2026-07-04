"""
MT5 PARALLEL OPTIMISATION – correctly shares data & models across workers
"""

import os, sys, time, itertools
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
from multiprocessing import Pool, cpu_count
from real_ai_service import RealAITrader

# ---------- CONFIG ----------
PAIRS = ['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NZDUSD','USDSGD']
START_DATE = '2020-01-01'
END_DATE = '2025-01-01'
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
LIMIT_COMBINATIONS = 100         # <-- change to 100 if you want

# These globals will be initialised inside each worker process
worker_cache = None
worker_ai = None

def fetch_mt5(pair, start, end):
    candidates = [pair, f"{pair}m", f"{pair}.", f"{pair}pro"]
    symbol = None
    for sym in candidates:
        if mt5.symbol_select(sym, True):
            symbol = sym
            break
    if not symbol: return None
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1,
                                 pd.to_datetime(start), pd.to_datetime(end))
    if rates is None or len(rates)==0: return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    return df[['open','high','low','close','volume']]

def simulate_trade_vectorized(df, entry_idx, signal, sl, tp, lot, pair):
    spread = SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY
    entry_price = df.iloc[entry_idx]['close']
    if signal == 'BUY': entry_price += spread
    else: entry_price -= spread
    subset = df.iloc[entry_idx + 1:]
    if subset.empty: return len(df)-1, df.iloc[-1]['close'], 0.0, 'End'
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

# ===== WORKER INITIALISER (receives data & AI) =====
def init_worker(cached, ai):
    global worker_cache, worker_ai
    worker_cache = cached
    worker_ai = ai

# ===== EVALUATOR (now uses worker_cache) =====
def evaluate_combination(params):
    global worker_cache, worker_ai
    all_trades = []
    for pair, df in worker_cache.items():
        balance = INITIAL_CAPITAL
        i = 100
        while i < len(df)-1:
            row = df.iloc[i]
            atr_val = row['atr']
            # Early ATR filter
            if 'JPY' in pair:
                if atr_val < params['atr_min_jpy'] or atr_val > params['atr_max_jpy']:
                    i += 1; continue
            else:
                if atr_val < params['atr_min_non_jpy'] or atr_val > params['atr_max_non_jpy']:
                    i += 1; continue

            sig = worker_ai.get_signal_from_row(
                row, pair,
                use_filters=False,    # already filtered above
                atr_min=params['atr_min_non_jpy'],
                atr_max=params['atr_max_non_jpy'],
                atr_min_jpy=params['atr_min_jpy'],
                atr_max_jpy=params['atr_max_jpy']
            )
            if not sig or sig['confidence'] < params['min_confidence']:
                i += 1; continue

            lot = calc_lot(balance, sig['entry'], sig['stop_loss'],
                           params['risk_percent'], pair)
            exit_idx, exit_price, pnl, reason = simulate_trade_vectorized(
                df, i, sig['signal'], sig['stop_loss'], sig['take_profit'], lot, pair
            )
            balance += pnl
            all_trades.append(pnl)
            i = exit_idx + 1

    if not all_trades: return None
    arr = np.array(all_trades)
    wins = np.sum(arr > 0)
    total = len(arr)
    total_pnl = arr.sum()
    gross_profit = arr[arr > 0].sum()
    gross_loss = abs(arr[arr < 0].sum())
    pf = gross_profit / gross_loss if gross_loss else float('inf')
    wr = wins / total if total else 0
    score = pf * wr
    return {**params, 'score': score, 'total_pnl': total_pnl,
            'win_rate': wr * 100, 'profit_factor': pf, 'trades': total}

def gen_combinations(grid, limit):
    keys = list(grid.keys())
    vals = list(grid.values())
    combos = list(itertools.product(*vals))
    if limit and len(combos) > limit:
        step = len(combos) // limit
        combos = combos[::step][:limit]
    return [dict(zip(keys, c)) for c in combos]

def main():
    print("="*60)
    print("🔧 MT5 PARALLEL OPTIMISATION (data‑sharing fixed)")
    print("="*60)

    if not mt5.initialize():
        print("❌ MT5 not running."); sys.exit(1)

    # Load AI in main process + pre‑fetch data + indicators
    ai = RealAITrader()
    cached_data = {}
    for pair in PAIRS:
        print(f"⬇️  Fetching {pair} …")
        df = fetch_mt5(pair, START_DATE, END_DATE)
        if df is not None and len(df) > 100:
            df = ai.add_indicators(df)
            if df is not None and len(df) > 100:
                cached_data[pair] = df
                print(f"   ✅ {pair} – {len(df)} bars after indicators")
            else:
                print(f"   ❌ indicator failure for {pair}")
        else:
            print(f"   ❌ {pair} – no data")
    if not cached_data:
        print("No data."); sys.exit(1)

    combos = gen_combinations(PARAM_GRID, LIMIT_COMBINATIONS)
    print(f"\n🚀 Testing {len(combos)} combinations in parallel …\n")

    results = []
    # Pass the data and AI to every worker via initargs
    with Pool(processes=cpu_count()-1,
              initializer=init_worker,
              initargs=(cached_data, ai)) as pool:
        for res in pool.imap_unordered(evaluate_combination, combos):
            if res:
                results.append(res)
                print(f"[{len(results):2d}/{len(combos)}] "
                      f"conf{res['min_confidence']:.2f} risk{res['risk_percent']:.1f}% → "
                      f"PnL ${res['total_pnl']:.0f} WR {res['win_rate']:.1f}% "
                      f"PF {res['profit_factor']:.2f} score {res['score']:.4f}")
            else:
                # You'll still see this rarely for combos that genuinely generate no trades
                pass

    if results:
        df_res = pd.DataFrame(results).sort_values('score', ascending=False)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = f"optimization_results_{ts}.csv"
        df_res.to_csv(csv_path, index=False)
        print(f"\n✅ Results saved to {csv_path}")
        print("\n🏆 TOP 5 PARAMETER SETS")
        for i, (_, row) in enumerate(df_res.head(5).iterrows()):
            print(f"#{i+1} Score {row['score']:.4f} | "
                  f"Conf {row['min_confidence']:.2f} Risk {row['risk_percent']:.1f}% | "
                  f"ATR non‑JPY {row['atr_min_non_jpy']:.5f}‑{row['atr_max_non_jpy']:.5f} "
                  f"JPY {row['atr_min_jpy']:.2f}‑{row['atr_max_jpy']:.2f} | "
                  f"PnL ${row['total_pnl']:.0f} WR {row['win_rate']:.1f}% PF {row['profit_factor']:.2f}")
    else:
        print("❌ No successful combinations.")

if __name__ == "__main__":
    main()