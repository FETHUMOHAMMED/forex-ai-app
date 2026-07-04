"""
WALK‑FORWARD VALIDATION – Self‑contained, with Telegram alert on completion.
Splits data into train/test windows, runs GA on each, measures out‑of‑sample performance,
and sends a summary to Telegram.
"""

import os, sys, json, time, random
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from real_ai_service import RealAITrader
from dotenv import load_dotenv
from notify.telegram_notifier import TelegramNotifier

load_dotenv()

# ---------- CONFIG ----------
PAIRS = ['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NZDUSD','USDSGD',
        'USDSEK','USDMXN','USDZAR','USDBRL','EURTRY','GBPZAR','USDPLN','USDCLP',
        'XAGUSD','XAUUSD']
TRAIN_MONTHS = 6
TEST_MONTHS  = 2
STEP_MONTHS  = 2
GENERATIONS_PER_WINDOW = 3
POPULATION_SIZE = 10
MUTATION_RATE = 0.2
CROSSOVER_RATE = 0.7

SPREAD_NON_JPY = 0.0002
SPREAD_JPY    = 0.02
COMMISSION    = 7.0
INITIAL_CAPITAL = 2000

GENE_SPACE = {
    'min_confidence':     (0.55, 0.70, 0.05),
    'risk_percent':       (0.1,  0.7,  0.05),
    'atr_min_non_jpy':    (0.0005, 0.0008, 0.00005),
    'atr_max_non_jpy':    (0.002,  0.005,  0.0005),
    'atr_min_jpy':        (0.07,  0.09,  0.005),
    'atr_max_jpy':        (0.20,  0.35,  0.05),
    'sl_atr_mult':        (2.0,   2.5,   0.1),
    'tp_atr_mult':        (2.0,   3.5,   0.1),
}

# ---- Gene helpers ----
def create_individual():
    genes = {}
    for key, (min_val, max_val, step) in GENE_SPACE.items():
        possible = np.arange(min_val, max_val + step/2, step)
        genes[key] = float(round(random.choice(possible), 6))
    return genes

def select_tournament(pop, scores, k=3):
    idx = random.sample(range(len(pop)), k)
    best = max(idx, key=lambda i: scores[i])
    return pop[best].copy()

# ---- Vectorized fitness evaluation ----
def fitness_vectorized(genes, cached):
    all_pnls = []
    for pair, df in cached.items():
        close = df['close'].values.astype(np.float64)
        high  = df['high'].values.astype(np.float64)
        low   = df['low'].values.astype(np.float64)
        atr   = df['atr'].values.astype(np.float64)
        ml_sig = df['ml_signal'].values.astype(np.int32)
        ml_conf = df['ml_conf'].values.astype(np.float64)
        ict_b = (df['fvg_buy'] | df['ob_buy'] | df['bb_buy'] | df['lv_buy'] | df['mss_buy']).values.astype(bool)
        ict_s = (df['fvg_sell'] | df['ob_sell'] | df['bb_sell'] | df['lv_sell'] | df['mss_sell']).values.astype(bool)

        spread_price = SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY
        n = len(close)

        if 'JPY' in pair:
            valid = (atr >= genes['atr_min_jpy']) & (atr <= genes['atr_max_jpy'])
        else:
            valid = (atr >= genes['atr_min_non_jpy']) & (atr <= genes['atr_max_non_jpy'])

        # Ensemble signals (vectorized)
        signal_mask = np.zeros(n, dtype=bool)
        signal_type = np.empty(n, dtype='U4')
        conf_vals = np.zeros(n, dtype=np.float64)

        cond = valid & ict_b & (ml_sig == 1) & (ml_conf > 0.55)
        signal_mask[cond]=True; signal_type[cond]='BUY'; conf_vals[cond]=ml_conf[cond]
        cond = valid & ict_s & (ml_sig == 0) & (ml_conf > 0.55)
        signal_mask[cond]=True; signal_type[cond]='SELL'; conf_vals[cond]=ml_conf[cond]
        cond = valid & (ml_conf > 0.65)
        signal_mask[cond]=True; signal_type[cond]=np.where(ml_sig[cond]==1,'BUY','SELL'); conf_vals[cond]=ml_conf[cond]
        cond = valid & ict_b & (ml_conf > 0.51) & ~signal_mask
        signal_mask[cond]=True; signal_type[cond]='BUY'; conf_vals[cond]=0.55
        cond = valid & ict_s & (ml_conf > 0.51) & ~signal_mask
        signal_mask[cond]=True; signal_type[cond]='SELL'; conf_vals[cond]=0.55
        cond = valid & (ml_conf > 0.51) & ~signal_mask
        signal_mask[cond]=True; signal_type[cond]=np.where(ml_sig[cond]==1,'BUY','SELL'); conf_vals[cond]=ml_conf[cond]
        signal_mask &= (conf_vals >= genes['min_confidence'])

        if not signal_mask.any():
            continue

        entry_idx = np.where(signal_mask)[0]
        entry_prices = close[entry_idx]
        atr_entry = atr[entry_idx]
        signals = signal_type[entry_idx]
        sl_mult = genes['sl_atr_mult']; tp_mult = genes['tp_atr_mult']

        sls = np.where(signals == 'BUY', entry_prices - atr_entry * sl_mult,
                       entry_prices + atr_entry * sl_mult)
        tps = np.where(signals == 'BUY', entry_prices + atr_entry * tp_mult,
                       entry_prices - atr_entry * tp_mult)

        risk_amount = INITIAL_CAPITAL * (genes['risk_percent'] / 100.0)
        pip_value = 0.01 if 'JPY' in pair else 0.0001
        sl_dist = np.abs(entry_prices - sls)
        sl_pips = sl_dist / pip_value
        sl_pips[sl_pips == 0] = 0.01
        lots = risk_amount / (sl_pips * 10)
        lots = np.clip(np.round(lots, 2), 0.01, 10.0)

        # Trade exit (vectorized loop)
        exit_idxs = np.full(len(entry_idx), n-1, dtype=int)
        exit_prices = close[exit_idxs]
        for k in range(len(entry_idx)):
            e_idx = entry_idx[k]; sl_val = sls[k]; tp_val = tps[k]; sig = signals[k]
            if e_idx >= n-1: continue
            future_high = high[e_idx+1:]; future_low = low[e_idx+1:]
            if sig == 'BUY':
                sl_hit = np.where(future_low <= sl_val)[0]
                tp_hit = np.where(future_high >= tp_val)[0]
            else:
                sl_hit = np.where(future_high >= sl_val)[0]
                tp_hit = np.where(future_low <= tp_val)[0]
            first_sl = sl_hit[0] if len(sl_hit) else np.inf
            first_tp = tp_hit[0] if len(tp_hit) else np.inf
            if first_sl == np.inf and first_tp == np.inf:
                exit_idxs[k] = n-1; exit_prices[k] = close[-1]
            elif first_sl <= first_tp:
                exit_idxs[k] = e_idx+1+int(first_sl); exit_prices[k] = sl_val
            else:
                exit_idxs[k] = e_idx+1+int(first_tp); exit_prices[k] = tp_val
            exit_idxs[k] = min(exit_idxs[k], n-1)

        pnls = np.where(signals == 'BUY',
                        (exit_prices - entry_prices) * lots * 100000,
                        (entry_prices - exit_prices) * lots * 100000)
        pnls -= spread_price * lots * 100000
        pnls -= lots * COMMISSION
        if 'JPY' in pair: pnls /= exit_prices
        all_pnls.extend(pnls.tolist())

    if not all_pnls: return -9999
    arr = np.array(all_pnls)
    wins = np.sum(arr > 0); total = len(arr)
    gp = arr[arr>0].sum(); gl = abs(arr[arr<0].sum())
    pf = gp/gl if gl else float('inf')
    wr = wins/total*100 if total else 0
    return pf * (wr/100)

# ---- Main Walk‑Forward ----
def walk_forward():
    print("="*60)
    print("🔬 WALK‑FORWARD VALIDATION (with Telegram alert)")
    print("="*60)

    if not mt5.initialize():
        print("❌ MT5 not running."); sys.exit(1)

    # Load 2 years of hourly data
    ai = RealAITrader()
    cached = {}
    for pair in PAIRS:
        print(f"⬇️  Fetching {pair} …")
        symbol = None
        for suffix in ['', 'm', '.', 'pro']:
            if mt5.symbol_select(pair+suffix, True): symbol = pair+suffix; break
        if not symbol:
            print(f"   ❌ Symbol not found"); continue
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1,
                                     pd.to_datetime('2023-01-01'),
                                     pd.to_datetime('2025-01-01'))
        if rates is None or len(rates)<100: continue
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume':'volume'}, inplace=True)
        df = df[['open','high','low','close','volume']]
        df = ai.add_indicators(df)
        if df is None or len(df)<100: continue
        # Precompute ML
        model = ai.models.get(pair)
        if model:
            feat_cols = ['rsi','macd','macd_signal','atr','volume_ratio',
                         'bb_upper','bb_lower','fvg_buy','fvg_sell',
                         'ob_buy','ob_sell','returns','high_low_ratio',
                         'bb_buy','bb_sell','lv_buy','lv_sell','mss_buy','mss_sell']
            X = df[feat_cols].fillna(0).values
            preds = model.predict(X)
            probs = model.predict_proba(X)
        else:
            preds = np.zeros(len(df), dtype=int); probs = np.ones((len(df),2))*0.5
        df = df.copy()
        df['ml_signal'] = preds
        df['ml_conf'] = np.where(preds==1, probs[:,1], probs[:,0])
        cached[pair] = df
        print(f"   ✅ {pair} – {len(df)} bars")

    if not cached:
        print("❌ No data."); sys.exit(1)

    start = pd.to_datetime('2023-01-01')
    end  = pd.to_datetime('2025-01-01')
    current = start
    results = []

    while current + pd.DateOffset(months=TRAIN_MONTHS+TEST_MONTHS) <= end:
        train_start = current
        train_end   = current + pd.DateOffset(months=TRAIN_MONTHS)
        test_start  = train_end
        test_end    = test_start + pd.DateOffset(months=TEST_MONTHS)

        train_cache, test_cache = {}, {}
        for pair, df in cached.items():
            tdf = df[(df.index >= train_start) & (df.index < train_end)]
            edf = df[(df.index >= test_start) & (df.index < test_end)]
            if len(tdf)>100 and len(edf)>100:
                train_cache[pair] = tdf
                test_cache[pair] = edf

        if len(train_cache) < 4:
            current += pd.DateOffset(months=STEP_MONTHS); continue

        print(f"\n📅 Train {train_start.date()}→{train_end.date()} | Test {test_start.date()}→{test_end.date()}")

        pop = [create_individual() for _ in range(POPULATION_SIZE)]
        best_score = -9999; best_genes = None
        for gen in range(GENERATIONS_PER_WINDOW):
            scores = [fitness_vectorized(ind, train_cache) for ind in pop]
            idx_best = scores.index(max(scores))
            if scores[idx_best] > best_score:
                best_score = scores[idx_best]; best_genes = pop[idx_best].copy()
            new_pop = [pop[idx_best].copy()]
            while len(new_pop) < POPULATION_SIZE:
                p1 = select_tournament(pop, scores, 3)
                p2 = select_tournament(pop, scores, 3)
                child = {k: (p1[k] if random.random()<CROSSOVER_RATE else p2[k]) for k in p1}
                if random.random() < MUTATION_RATE:
                    k = random.choice(list(GENE_SPACE.keys()))
                    mi, ma, st = GENE_SPACE[k]
                    possible = np.arange(mi, ma+st/2, st)
                    child[k] = float(random.choice(possible))
                new_pop.append(child)
            pop = new_pop
        print(f"   Best Train Score: {best_score:.4f}")

        test_score = fitness_vectorized(best_genes, test_cache) if best_genes else -9999
        results.append({'train_start': train_start, 'test_start': test_start, 'test_score': test_score})
        print(f"   Test Score: {test_score:.4f}")
        current += pd.DateOffset(months=STEP_MONTHS)

    if results:
        avg = np.mean([r['test_score'] for r in results])
        print("\n" + "="*60)
        print("📊 WALK‑FORWARD RESULTS")
        print("="*60)
        for r in results:
            print(f"{r['train_start'].date()} → {r['test_start'].date()}  out‑of‑sample: {r['test_score']:.4f}")
        print(f"\n📈 Average out‑of‑sample score: {avg:.4f}")
        if avg > 0.4:
            status = "✅ ROBUST"
            print("✅ Strategy is robust.")
        else:
            status = "⚠️ CHECK"
            print("⚠️ Strategy may be overfitting – consider a simpler gene space.")

        # ── Telegram notification ──
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id   = os.getenv('TELEGRAM_CHAT_ID')
        if bot_token and chat_id:
            notifier = TelegramNotifier(bot_token, chat_id)
            best_window = max(results, key=lambda r: r['test_score'])
            worst_window = min(results, key=lambda r: r['test_score'])
            msg = (
                f"📊 Walk‑Forward Completed\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Periods tested: {len(results)}\n"
                f"Avg out‑of‑sample score: {avg:.4f}\n"
                f"Status: {status}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Best window: {best_window['test_start'].date()} → {best_window['test_score']:.4f}\n"
                f"Worst window: {worst_window['test_start'].date()} → {worst_window['test_score']:.4f}"
            )
            notifier.send_message(msg)
            print("📲 Telegram notification sent.")
    else:
        print("❌ No valid windows.")

if __name__ == "__main__":
    walk_forward()