"""
FULLY AUTOMATED GA PIPELINE – VECTORIZED FOR SPEED
1. Download fresh tick data.
2. Precompute ML signals & convert to NumPy arrays.
3. Run GA with vectorized fitness evaluation (fast!).
4. Update config.json for target account.
"""

import os, sys, json, time, random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from real_ai_service import RealAITrader

# ---------- CONFIG ----------
PAIRS = ['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NZDUSD','USDSGD',
        'USDSEK','USDMXN','USDZAR','USDBRL','EURTRY','GBPZAR','USDPLN','USDCLP',
        'XAGUSD','XAUUSD']
TICK_CSV_DIR = "data"
CONFIG_PATH = "config.json"

GENE_SPACE = {
    'min_confidence':     (0.50, 0.70, 0.05),
    'risk_percent':       (0.1, 1.5, 0.1),
    'atr_min_non_jpy':    (0.0002, 0.0010, 0.0001),
    'atr_max_non_jpy':    (0.0020, 0.0050, 0.0005),
    'atr_min_jpy':        (0.02, 0.08, 0.01),
    'atr_max_jpy':        (0.20, 0.50, 0.05),
    'sl_atr_mult':        (1.0, 2.5, 0.1),
    'tp_atr_mult':        (2.0, 4.0, 0.1),
}

POPULATION_SIZE = 16    # slightly smaller for speed
GENERATIONS = 10
MUTATION_RATE = 0.2
CROSSOVER_RATE = 0.7

TARGET_ACCOUNT_NAME = "Demo2"

SPREAD_NON_JPY = 0.0002
SPREAD_JPY    = 0.02
COMMISSION    = 7.0
INITIAL_CAPITAL = 2000

# ---- Step 1: Download fresh tick data ----
def download_fresh_ticks():
    print("⬇️  Downloading fresh tick data …")
    if not mt5.initialize():
        print("❌ MT5 not running."); return False
    END = datetime.now()
    START = END - timedelta(days=120)
    for pair in PAIRS:
        candidates = [pair, f"{pair}m", f"{pair}.", f"{pair}pro"]
        symbol = None
        for sym in candidates:
            if mt5.symbol_select(sym, True):
                symbol = sym
                break
        if not symbol:
            print(f"   ❌ Symbol not found for {pair}")
            continue
        all_ticks = []
        chunk_start = START
        while chunk_start < END:
            chunk_end = min(chunk_start + timedelta(days=30), END)
            ticks = mt5.copy_ticks_range(symbol, chunk_start, chunk_end, mt5.COPY_TICKS_ALL)
            if ticks is not None and len(ticks) > 0:
                all_ticks.append(ticks)
            chunk_start = chunk_end + timedelta(seconds=1)
        if all_ticks:
            combined = np.concatenate(all_ticks)
            df = pd.DataFrame(combined)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df = df[['bid', 'ask', 'volume']]
            filename = os.path.join(TICK_CSV_DIR, f"{pair}_ticks.csv")
            df.to_csv(filename)
            print(f"   ✅ {pair} – {len(df)} ticks saved")
    mt5.shutdown()
    return True

# ---- Step 2: Prepare data and precompute ML signals as NumPy arrays ----
def prepare_data():
    print("🧮 Loading data & precomputing ML …")
    ai = RealAITrader()
    cached = {}
    for pair in PAIRS:
        path = os.path.join(TICK_CSV_DIR, f"{pair}_ticks.csv")
        if not os.path.exists(path):
            continue
        ticks = pd.read_csv(path, index_col=0, parse_dates=True)
        ticks['mid'] = (ticks['bid'] + ticks['ask']) / 2
        ohlc = ticks['mid'].resample('1min').ohlc()
        ohlc.columns = ['open','high','low','close']
        ohlc['volume'] = ticks['volume'].resample('1min').sum()
        ohlc = ohlc.dropna()
        ohlc = ai.add_indicators(ohlc)
        if ohlc is None or len(ohlc) < 100:
            continue

        # Precompute ML signals
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
        else:
            preds = np.zeros(len(ohlc), dtype=int)
            probs = np.ones((len(ohlc), 2)) * 0.5

        # Build fast arrays
        data = {
            'close': ohlc['close'].values.astype(np.float64),
            'high':  ohlc['high'].values.astype(np.float64),
            'low':   ohlc['low'].values.astype(np.float64),
            'atr':   ohlc['atr'].values.astype(np.float64),
            'ml_signal': preds.astype(np.int32),
            'ml_conf':   np.where(preds==1, probs[:,1], probs[:,0]).astype(np.float64),
            'ict_buy':   (ohlc['fvg_buy'] | ohlc['ob_buy'] | ohlc['bb_buy'] | ohlc['lv_buy'] | ohlc['mss_buy']).values.astype(bool),
            'ict_sell':  (ohlc['fvg_sell'] | ohlc['ob_sell'] | ohlc['bb_sell'] | ohlc['lv_sell'] | ohlc['mss_sell']).values.astype(bool),
            'n': len(ohlc)
        }
        cached[pair] = data
        print(f"   ✅ {pair} – {len(ohlc)} bars ready")
    return ai, cached

# ---- Gene helpers ----
def create_individual():
    genes = {}
    for key, (min_val, max_val, step) in GENE_SPACE.items():
        possible = np.arange(min_val, max_val + step/2, step)
        genes[key] = float(round(random.choice(possible), 6))
    return genes

# ---- VECTORIZED fitness evaluation (no per-bar loops) ----
def fitness_vectorized(genes, cached):
    all_pnls = []
    for pair, d in cached.items():
        n = d['n']
        close = d['close']; high = d['high']; low = d['low']
        atr = d['atr']; ml_sig = d['ml_signal']; ml_conf = d['ml_conf']
        ict_b = d['ict_buy']; ict_s = d['ict_sell']
        spread_price = SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY

        # Filter bars by ATR
        if 'JPY' in pair:
            valid = (atr >= genes['atr_min_jpy']) & (atr <= genes['atr_max_jpy'])
        else:
            valid = (atr >= genes['atr_min_non_jpy']) & (atr <= genes['atr_max_non_jpy'])

        # Generate ensemble signals (vectorized)
        signal_mask = np.zeros(n, dtype=bool)
        signal_type = np.empty(n, dtype='U4')   # BUY/SELL
        conf_vals = np.zeros(n, dtype=np.float64)

        cond = valid & ict_b & (ml_sig == 1) & (ml_conf > 0.55)
        signal_mask[cond] = True; signal_type[cond] = 'BUY'; conf_vals[cond] = ml_conf[cond]
        cond = valid & ict_s & (ml_sig == 0) & (ml_conf > 0.55)
        signal_mask[cond] = True; signal_type[cond] = 'SELL'; conf_vals[cond] = ml_conf[cond]
        cond = valid & (ml_conf > 0.65)
        signal_mask[cond] = True; signal_type[cond] = np.where(ml_sig[cond]==1, 'BUY', 'SELL'); conf_vals[cond] = ml_conf[cond]
        cond = valid & ict_b & (ml_conf > 0.51) & ~signal_mask
        signal_mask[cond] = True; signal_type[cond] = 'BUY'; conf_vals[cond] = 0.55
        cond = valid & ict_s & (ml_conf > 0.51) & ~signal_mask
        signal_mask[cond] = True; signal_type[cond] = 'SELL'; conf_vals[cond] = 0.55
        cond = valid & (ml_conf > 0.51) & ~signal_mask
        signal_mask[cond] = True; signal_type[cond] = np.where(ml_sig[cond]==1, 'BUY', 'SELL'); conf_vals[cond] = ml_conf[cond]
        signal_mask &= (conf_vals >= genes['min_confidence'])

        if not signal_mask.any():
            continue

        # Entry indices
        entry_idx = np.where(signal_mask)[0]
        entry_prices = close[entry_idx]
        atr_entry = atr[entry_idx]
        signals = signal_type[entry_idx]
        sl_mult = genes['sl_atr_mult']; tp_mult = genes['tp_atr_mult']

        sls = np.where(signals == 'BUY', entry_prices - atr_entry * sl_mult,
                       entry_prices + atr_entry * sl_mult)
        tps = np.where(signals == 'BUY', entry_prices + atr_entry * tp_mult,
                       entry_prices - atr_entry * tp_mult)

        # Lot sizes (based on balance – we'll assume fixed initial capital per trade)
        # For simplicity, we assume risk amount = INITIAL_CAPITAL * risk_percent
        risk_amount = INITIAL_CAPITAL * (genes['risk_percent'] / 100.0)
        pip_values = np.where(np.char.find(PAIRS, 'JPY') != -1, 0.01, 0.0001)   # needs pair check; we'll handle per pair later
        # Actually we need pip_value per pair, so we'll compute lot after loop.
        # Instead, let's compute lot array in a vectorized way.
        if 'JPY' in pair:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        sl_dist = np.abs(entry_prices - sls)
        with np.errstate(divide='ignore', invalid='ignore'):
            sl_pips = sl_dist / pip_value
        sl_pips[sl_pips == 0] = 0.01
        lots = risk_amount / (sl_pips * 10)
        lots = np.clip(np.round(lots, 2), 0.01, 10.0)

        # Vectorized trade exit simulation
        # We'll use a trick: for each entry, we look ahead and find first SL or TP hit.
        # This can be done with cumulative minimum/maximum and searchsorted.
        # We'll implement a fast vectorized function.
        exit_idxs = np.full(len(entry_idx), n-1, dtype=int)
        exit_prices = close[exit_idxs]
        reasons = np.array(['End']*len(entry_idx), dtype='U4')

        for k in range(len(entry_idx)):
            e_idx = entry_idx[k]
            sl_val = sls[k]
            tp_val = tps[k]
            sig = signals[k]
            # Look forward
            if e_idx >= n-1:
                continue
            future_high = high[e_idx+1:]
            future_low = low[e_idx+1:]
            if sig == 'BUY':
                sl_hit = np.where(future_low <= sl_val)[0]
                tp_hit = np.where(future_high >= tp_val)[0]
            else:
                sl_hit = np.where(future_high >= sl_val)[0]
                tp_hit = np.where(future_low <= tp_val)[0]
            first_sl = sl_hit[0] if len(sl_hit) else np.inf
            first_tp = tp_hit[0] if len(tp_hit) else np.inf
            if first_sl == np.inf and first_tp == np.inf:
                exit_idxs[k] = n-1
                exit_prices[k] = close[-1]
                reasons[k] = 'End'
            elif first_sl <= first_tp:
                exit_idxs[k] = e_idx + 1 + int(first_sl)
                exit_prices[k] = sl_val
                reasons[k] = 'SL'
            else:
                exit_idxs[k] = e_idx + 1 + int(first_tp)
                exit_prices[k] = tp_val
                reasons[k] = 'TP'
            # clamp
            exit_idxs[k] = min(exit_idxs[k], n-1)

        # PnL calculation vectorized
        pnls = np.where(signals == 'BUY',
                        (exit_prices - entry_prices) * lots * 100000,
                        (entry_prices - exit_prices) * lots * 100000)
        # spread cost
        pnls -= spread_price * lots * 100000
        pnls -= lots * COMMISSION
        if 'JPY' in pair:
            pnls /= exit_prices   # approximate
        all_pnls.extend(pnls.tolist())

    if not all_pnls:
        return -9999
    arr = np.array(all_pnls)
    wins = np.sum(arr > 0)
    total = len(arr)
    gp = arr[arr > 0].sum()
    gl = abs(arr[arr < 0].sum())
    pf = gp / gl if gl else float('inf')
    wr = wins / total * 100 if total else 0
    return pf * (wr / 100)

# ---- GA core ----
def select_tournament(pop, scores, k=3):
    idx = random.sample(range(len(pop)), k)
    best = max(idx, key=lambda i: scores[i])
    return pop[best].copy()

def main():
    if not download_fresh_ticks():
        return
    ai, cached = prepare_data()
    if not cached:
        print("❌ No data."); return

    print(f"\n🧬 GA Evolving (vectorized) …")
    pop = [create_individual() for _ in range(POPULATION_SIZE)]
    best_score = -9999
    best_genes = None
    for gen in range(GENERATIONS):
        t0 = time.time()
        scores = [fitness_vectorized(ind, cached) for ind in pop]
        gen_best = max(scores)
        gen_best_idx = scores.index(gen_best)
        if gen_best > best_score:
            best_score = gen_best
            best_genes = pop[gen_best_idx].copy()
        print(f"Gen {gen+1}/{GENERATIONS} – Best: {gen_best:.4f}  Avg: {np.mean(scores):.4f}  ⏱️{time.time()-t0:.1f}s")
        new_pop = [pop[gen_best_idx].copy()]   # elitism
        for _ in range(POPULATION_SIZE-1):
            p1 = select_tournament(pop, scores)
            p2 = select_tournament(pop, scores)
            child = {k: (p1[k] if random.random()<CROSSOVER_RATE else p2[k]) for k in p1}
            if random.random() < MUTATION_RATE:
                k = random.choice(list(GENE_SPACE.keys()))
                min_v, max_v, step = GENE_SPACE[k]
                possible = np.arange(min_v, max_v+step/2, step)
                child[k] = float(random.choice(possible))
            new_pop.append(child)
        pop = new_pop

    print(f"\n🎉 Best Score: {best_score:.4f}")
    print(json.dumps(best_genes, indent=2))

    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    for acc in config.get('accounts', []):
        if acc.get('name') == TARGET_ACCOUNT_NAME:
            acc['min_confidence'] = best_genes['min_confidence']
            acc['risk_percent'] = best_genes['risk_percent']
            acc['atr_min_non_jpy'] = best_genes['atr_min_non_jpy']
            acc['atr_max_non_jpy'] = best_genes['atr_max_non_jpy']
            acc['atr_min_jpy'] = best_genes['atr_min_jpy']
            acc['atr_max_jpy'] = best_genes['atr_max_jpy']
            print(f"✅ Updated {TARGET_ACCOUNT_NAME}")
            break
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

if __name__ == "__main__":
    main()