"""
ML+ICT TICK BACKTEST – Precomputed ML Predictions (Fast & Bulletproof)
All loop variables are plain NumPy arrays – no KeyErrors.
"""

import os, sys, time, itertools
import numpy as np
import pandas as pd
from datetime import datetime
from real_ai_service import RealAITrader

# ---------- CONFIG ----------
PAIRS = ['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NZDUSD','USDSGD']
INITIAL_CAPITAL = 2000
SPREAD_NON_JPY = 0.0002
SPREAD_JPY    = 0.02
COMMISSION    = 7.0

PARAM_GRID = {
    'min_confidence': [0.55, 0.60, 0.65],
    'risk_percent': [0.3, 0.5, 0.7],
    'atr_min_non_jpy': [0.0005, 0.0007, 0.0009],
    'atr_max_non_jpy': [0.0030, 0.0035, 0.0040],
    'atr_min_jpy': [0.04, 0.05, 0.06],
    'atr_max_jpy': [0.30, 0.35, 0.40]
}
LIMIT_COMBOS = 100

def load_tick_csv(pair):
    path = f"data/{pair}_ticks.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, index_col=0, parse_dates=True)

def resample_to_min(tick_df):
    tick_df['mid'] = (tick_df['bid'] + tick_df['ask']) / 2
    ohlc = tick_df['mid'].resample('1min').ohlc()
    ohlc.columns = ['open','high','low','close']
    ohlc['volume'] = tick_df['volume'].resample('1min').sum()
    return ohlc.dropna()

def simulate_trade_min(df, entry_idx, signal, sl, tp, lot, pair):
    spread_price = SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY
    entry_price = df.iloc[entry_idx]['close'] + (spread_price if signal=='BUY' else -spread_price)
    subset = df.iloc[entry_idx+1:]
    if subset.empty:
        return len(df)-1, df.iloc[-1]['close'], 0.0, 'End'
    h, l, c = subset['high'].values, subset['low'].values, subset['close'].values
    sl_hit = np.where(l <= sl)[0] if signal=='BUY' else np.where(h >= sl)[0]
    tp_hit = np.where(h >= tp)[0] if signal=='BUY' else np.where(l <= tp)[0]
    f_sl = sl_hit[0] if len(sl_hit) else np.inf
    f_tp = tp_hit[0] if len(tp_hit) else np.inf
    if f_sl==np.inf and f_tp==np.inf:
        ei, ep, reason = len(subset)-1, c[-1], 'End'
    elif f_sl <= f_tp:
        ei, ep, reason = int(f_sl), sl, 'SL'
    else:
        ei, ep, reason = int(f_tp), tp, 'TP'
    actual = min(entry_idx+1+ei, len(df)-1)
    pnl = (ep-entry_price)*lot*100000 if signal=='BUY' else (entry_price-ep)*lot*100000
    pnl -= lot*COMMISSION
    if 'JPY' in pair: pnl /= ep
    return actual, ep, pnl, reason

def calc_lot(balance, entry, sl, risk_percent, pair):
    risk_amount = balance*(risk_percent/100.0)
    if abs(entry-sl)==0: return 0.01
    pip_value = 0.01 if 'JPY' in pair else 0.0001
    sl_pips = abs(entry-sl)/pip_value
    lot = risk_amount/(sl_pips*10)
    return max(0.01, min(round(lot,2), 10.0))

def gen_combos(grid, limit):
    keys, vals = list(grid.keys()), list(grid.values())
    combos = list(itertools.product(*vals))
    if limit and len(combos)>limit:
        step = max(1,len(combos)//limit)
        combos = combos[::step][:limit]
    return [dict(zip(keys,c)) for c in combos]

def main():
    print("="*60)
    print("🤖 ML+ICT TICK BACKTEST (Precomputed ML – Bulletproof)")
    print("="*60)

    ai = RealAITrader()

    cached = {}
    for pair in PAIRS:
        print(f"📂 {pair} …")
        ticks = load_tick_csv(pair)
        if ticks is None: continue
        ohlc = resample_to_min(ticks)
        if len(ohlc)<100: continue
        ohlc = ai.add_indicators(ohlc)
        if ohlc is None or len(ohlc)<100: continue

        model = ai.models.get(pair)
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

        cached[pair] = ohlc
        print(f"   ✅ {pair} – {len(ohlc)} bars, ML precomputed")

    if not cached:
        print("No data."); sys.exit(1)

    combos = gen_combos(PARAM_GRID, LIMIT_COMBOS)
    print(f"\n🚀 {len(combos)} ML‑powered combinations (precomputed) …\n")
    results = []

    for idx, params in enumerate(combos, 1):
        t0 = time.time()
        all_trades = []
        for pair, df in cached.items():
            balance = INITIAL_CAPITAL

            # ----- convert EVERYTHING to plain numpy arrays (no pandas Series) -----
            close   = np.asarray(df['close'].values, dtype=np.float64)
            high    = np.asarray(df['high'].values,  dtype=np.float64)
            low     = np.asarray(df['low'].values,   dtype=np.float64)
            atr     = np.asarray(df['atr'].values,   dtype=np.float64)
            ml_sig  = np.asarray(df['ml_signal'].values, dtype=np.int32)
            ml_conf = np.asarray(df['ml_confidence'].values, dtype=np.float64)
            fvg_b   = np.asarray(df['fvg_buy'].values, dtype=np.bool_)
            fvg_s   = np.asarray(df['fvg_sell'].values, dtype=np.bool_)
            ob_b    = np.asarray(df['ob_buy'].values, dtype=np.bool_)
            ob_s    = np.asarray(df['ob_sell'].values, dtype=np.bool_)
            bb_b    = np.asarray(df['bb_buy'].values, dtype=np.bool_)
            bb_s    = np.asarray(df['bb_sell'].values, dtype=np.bool_)
            lv_b    = np.asarray(df['lv_buy'].values, dtype=np.bool_)
            lv_s    = np.asarray(df['lv_sell'].values, dtype=np.bool_)
            mss_b   = np.asarray(df['mss_buy'].values, dtype=np.bool_)
            mss_s   = np.asarray(df['mss_sell'].values, dtype=np.bool_)

            i = 100
            while i < len(df)-1:
                a = atr[i]
                if pd.isna(a):
                    i += 1; continue
                if 'JPY' in pair:
                    if a < params['atr_min_jpy'] or a > params['atr_max_jpy']:
                        i += 1; continue
                else:
                    if a < params['atr_min_non_jpy'] or a > params['atr_max_non_jpy']:
                        i += 1; continue

                ict_buy = fvg_b[i] or ob_b[i] or bb_b[i] or lv_b[i] or mss_b[i]
                ict_sell = fvg_s[i] or ob_s[i] or bb_s[i] or lv_s[i] or mss_s[i]

                ml_pred = ml_sig[i]
                mc = ml_conf[i]

                signal = None
                conf = 0.5
                if ict_buy and ml_pred == 1 and mc > 0.55:
                    signal = 'BUY'; conf = mc
                elif ict_sell and ml_pred == 0 and mc > 0.55:
                    signal = 'SELL'; conf = mc
                elif mc > 0.65:
                    signal = 'BUY' if ml_pred == 1 else 'SELL'; conf = mc
                elif ict_buy and mc > 0.51:
                    signal = 'BUY'; conf = 0.55
                elif ict_sell and mc > 0.51:
                    signal = 'SELL'; conf = 0.55
                elif mc > 0.51:
                    signal = 'BUY' if ml_pred == 1 else 'SELL'; conf = mc

                if not signal or conf < params['min_confidence']:
                    i += 1; continue

                entry = close[i]
                sl_mult, tp_mult = 1.5, 2.5
                if signal == 'BUY':
                    sl = entry - a * sl_mult
                    tp = entry + a * tp_mult
                else:
                    sl = entry + a * sl_mult
                    tp = entry - a * tp_mult

                lot = calc_lot(balance, entry, sl, params['risk_percent'], pair)
                ei, ep, pnl, _ = simulate_trade_min(df, i, signal, sl, tp, lot, pair)
                balance += pnl
                all_trades.append(pnl)
                i = ei + 1

        elapsed = time.time()-t0
        if all_trades:
            arr = np.array(all_trades)
            wins = np.sum(arr>0)
            total, tot_pnl = len(arr), arr.sum()
            gp = arr[arr>0].sum()
            gl = abs(arr[arr<0].sum())
            pf = gp/gl if gl else float('inf')
            wr = wins/total*100
            score = pf*(wr/100)
            results.append({**params, 'score':score, 'total_pnl':tot_pnl,
                            'win_rate':wr, 'pf':pf, 'trades':total})
            print(f"[{idx:2d}/{len(combos)}] conf{params['min_confidence']:.2f} "
                  f"risk{params['risk_percent']:.1f}% → PnL ${tot_pnl:.0f} "
                  f"WR {wr:.1f}% PF {pf:.2f} score {score:.4f} ⏱️{elapsed:.1f}s")
        else:
            print(f"[{idx:2d}/{len(combos)}] no trades ⏱️{elapsed:.1f}s")

    if results:
        df_res = pd.DataFrame(results).sort_values('score', ascending=False)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = f"ml_optimization_{ts}.csv"
        df_res.to_csv(csv_path, index=False)
        print(f"\n✅ Results saved to {csv_path}")
        print("\n🏆 TOP 5 PARAMETER SETS")
        for i, (_, row) in enumerate(df_res.head(5).iterrows()):
            print(f"#{i+1} Score {row['score']:.4f} | Conf {row['min_confidence']:.2f} Risk {row['risk_percent']:.1f}% | "
                  f"ATR non‑JPY {row['atr_min_non_jpy']:.5f}‑{row['atr_max_non_jpy']:.5f} "
                  f"JPY {row['atr_min_jpy']:.2f}‑{row['atr_max_jpy']:.2f} | "
                  f"PnL ${row['total_pnl']:.0f} WR {row['win_rate']:.1f}% PF {row['pf']:.2f}")
    else:
        print("❌ No successful combinations.")

if __name__ == "__main__":
    main()