"""
EVOLVE_REGIME_PARAMS.PY
Robust GA optimizer – trending no H4, wider SL/TP, min ATR width, stability penalty.
"""

import os
import json
import random
import warnings
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
from numba import njit
from real_ai_service import RealAITrader
from features import FEATURE_COLUMNS

warnings.filterwarnings("ignore")

# =========================================================
# CONFIG
# =========================================================

PAIRS = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'USDSGD'
]

TICK_CSV_DIR = "data"
CONFIG_PATH = "config.json"

INITIAL_CAPITAL = 2000

POPULATION_SIZE = 24
GENERATIONS = 12

MUTATION_RATE = 0.20
CROSSOVER_RATE = 0.70

SPREAD_NON_JPY = 0.0002
SPREAD_JPY = 0.02

COMMISSION = 7.0
MIN_TRADES_REQUIRED = 20

COOLDOWN_BARS = 12
SESSION_START = 7
SESSION_END = 18

# =========================================================
# GENE SPACE (will be overridden for trending)
# =========================================================

GENE_SPACE = {
    'min_confidence': (0.50, 0.65, 0.02),
    'risk_percent': (0.10, 0.35, 0.05),
    'atr_min_non_jpy': (0.0004, 0.0020, 0.0001),
    'atr_max_non_jpy': (0.0020, 0.0080, 0.0005),
    'atr_min_jpy': (0.04, 0.12, 0.01),
    'atr_max_jpy': (0.20, 0.50, 0.05),
    'sl_atr_mult': (1.5, 3.5, 0.1),
    'tp_atr_mult': (1.5, 4.0, 0.1),
}

# =========================================================
# FAST EXIT ENGINE (Numba)
# =========================================================

@njit(fastmath=True)
def fast_exit_scan(entry_idx, signals_int, high, low, close, sls, tps, n):
    m = len(entry_idx)
    exit_idxs = np.full(m, n - 1, dtype=np.int64)
    exit_prices = np.empty(m, dtype=np.float64)

    for k in range(m):
        e_idx = entry_idx[k]
        sl = sls[k]
        tp = tps[k]
        is_buy = signals_int[k] == 1
        found = False
        for j in range(e_idx + 1, n):
            if is_buy:
                if low[j] <= sl:
                    exit_idxs[k] = j
                    exit_prices[k] = sl
                    found = True
                    break
                if high[j] >= tp:
                    exit_idxs[k] = j
                    exit_prices[k] = tp
                    found = True
                    break
            else:
                if high[j] >= sl:
                    exit_idxs[k] = j
                    exit_prices[k] = sl
                    found = True
                    break
                if low[j] <= tp:
                    exit_idxs[k] = j
                    exit_prices[k] = tp
                    found = True
                    break
        if not found:
            exit_prices[k] = close[-1]
    return exit_idxs, exit_prices

# =========================================================
# GA HELPERS
# =========================================================

def create_individual():
    genes = {}
    for key, (mn, mx, step) in GENE_SPACE.items():
        vals = np.arange(mn, mx + step / 2, step)
        genes[key] = float(round(random.choice(vals), 6))
    return genes

def select_tournament(population, scores, k=3):
    idx = random.sample(range(len(population)), k)
    best = max(idx, key=lambda i: scores[i])
    return population[best].copy()

# =========================================================
# ROBUST FITNESS
# =========================================================

def fitness_vectorized(genes, cached, regime_name=None):
    all_pnls = []

    for pair, df in cached.items():
        close = df['close'].values.astype(np.float64)
        high = df['high'].values.astype(np.float64)
        low = df['low'].values.astype(np.float64)
        atr = df['atr'].values.astype(np.float64)
        ml_sig = df['ml_signal'].values.astype(np.int32)
        ml_conf = df['ml_conf'].values.astype(np.float64)
        h4_up = df['h4_uptrend'].values.astype(bool)
        h4_down = df['h4_downtrend'].values.astype(bool)

        ict_buy = (df['fvg_buy'] | df['ob_buy'] | df['bb_buy'] |
                   df['lv_buy'] | df['mss_buy']).values.astype(bool)
        ict_sell = (df['fvg_sell'] | df['ob_sell'] | df['bb_sell'] |
                    df['lv_sell'] | df['mss_sell']).values.astype(bool)

        spread_pct = df['spread_pct'].values.astype(np.float64)
        n = len(close)
        spread_price = SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY

        # ATR filter
        if 'JPY' in pair:
            atr_ok = (atr >= genes['atr_min_jpy']) & (atr <= genes['atr_max_jpy'])
        else:
            atr_ok = (atr >= genes['atr_min_non_jpy']) & (atr <= genes['atr_max_non_jpy'])

        # Enforce minimum ATR width for volatile
        if regime_name == 'volatile':
            if 'JPY' in pair:
                atr_width = genes['atr_max_jpy'] - genes['atr_min_jpy']
                if atr_width < 0.08:
                    return -2.0
            else:
                atr_width = genes['atr_max_non_jpy'] - genes['atr_min_non_jpy']
                if atr_width < 0.0015:
                    return -2.0

        # Signal logic – trending has NO H4 filter
        if regime_name == 'trending':
            # Trending: ICT + ML only, no H4 requirement
            buy_signal = (atr_ok & ict_buy & (ml_sig == 1) &
                          (ml_conf >= genes['min_confidence']))
            sell_signal = (atr_ok & ict_sell & (ml_sig == 0) &
                           (ml_conf >= genes['min_confidence']))
        else:
            # Other regimes: keep H4 filter if desired (currently no H4)
            # We'll just use same as above, no H4 for simplicity
            buy_signal = (atr_ok & ict_buy & (ml_sig == 1) &
                          (ml_conf >= genes['min_confidence']))
            sell_signal = (atr_ok & ict_sell & (ml_sig == 0) &
                           (ml_conf >= genes['min_confidence']))

        signal_mask = buy_signal | sell_signal
        if not signal_mask.any():
            continue

        entry_idx = np.where(signal_mask)[0]

        # Session filter
        hours = df.index[entry_idx].hour
        session_ok = (hours >= SESSION_START) & (hours <= SESSION_END)
        entry_idx = entry_idx[session_ok]
        if len(entry_idx) == 0:
            continue

        # Cooldown filter
        if len(entry_idx) > 1:
            keep = [entry_idx[0]]
            for idx in entry_idx[1:]:
                if idx - keep[-1] >= COOLDOWN_BARS:
                    keep.append(idx)
            entry_idx = np.array(keep)
        if len(entry_idx) == 0:
            continue

        signals = np.where(buy_signal[entry_idx], 'BUY', 'SELL')
        entry_prices = close[entry_idx]
        atr_entry = atr[entry_idx]

        sl_mult = genes['sl_atr_mult']
        tp_mult = genes['tp_atr_mult']

        sls = np.where(signals == 'BUY',
                       entry_prices - atr_entry * sl_mult,
                       entry_prices + atr_entry * sl_mult)
        tps = np.where(signals == 'BUY',
                       entry_prices + atr_entry * tp_mult,
                       entry_prices - atr_entry * tp_mult)

        # Position sizing
        risk_amount = INITIAL_CAPITAL * (genes['risk_percent'] / 100.0)
        pip_value = 0.01 if 'JPY' in pair else 0.0001
        sl_dist = np.abs(entry_prices - sls)
        sl_pips = sl_dist / pip_value
        sl_pips[sl_pips == 0] = 0.01
        lots = risk_amount / (sl_pips * 10)
        lots = np.clip(np.round(lots, 2), 0.01, 5.0)

        # Exit scan
        signals_int = np.where(signals == 'BUY', 1, 0).astype(np.int64)
        exit_idxs, exit_prices = fast_exit_scan(entry_idx.astype(np.int64),
                                                signals_int, high, low, close,
                                                sls, tps, n)

        # PnL
        pnls = np.where(signals == 'BUY',
                        (exit_prices - entry_prices) * lots * 100_000,
                        (entry_prices - exit_prices) * lots * 100_000)
        pnls -= spread_price * lots * 100_000
        pnls -= lots * COMMISSION
        if 'JPY' in pair:
            pnls /= exit_prices
        all_pnls.extend(pnls.tolist())

    # =========================================================
    # FINAL METRICS (with heavy trade‑frequency incentive)
    # =========================================================
    if len(all_pnls) < 10:
        return -2.0

    arr = np.array(all_pnls)
    wins = np.sum(arr > 0)
    total = len(arr)
    gp = arr[arr > 0].sum()
    gl = abs(arr[arr < 0].sum())

    # PF clamp
    if gl == 0 and gp > 0:
        pf = 3.0
    elif gl == 0:
        pf = 0.0
    else:
        pf = gp / gl
    pf = min(pf, 5.0)

    wr = wins / total if total > 0 else 0.0
    expectancy = arr.mean()
    expectancy = min(max(expectancy, -10.0), 10.0)

    equity = np.cumsum(arr)
    max_dd = np.min(equity - np.maximum.accumulate(equity)) if len(equity) > 1 else 0.0

    sharpe_like = arr.mean() / (arr.std() + 1e-9)
    sharpe_like = min(max(sharpe_like, -3.0), 3.0)

    trade_factor = min(total / 300.0, 1.0)

    base_score = (
        pf * 0.25 +
        wr * 0.15 +
        (expectancy / 20.0) * 0.15 +
        sharpe_like * 0.15
    )

    score = base_score * trade_factor

    score -= abs(max_dd) / 1500.0

    if total < 50:
        score -= 1.0
    if total < 30:
        score -= 2.0

    if pf < 1.05:
        score -= 1.0
    if wr < 0.45:
        score -= 0.5
    if expectancy <= 0.0:
        score -= 1.0

    # ---------- Parameter stability penalty ----------
    if genes['tp_atr_mult'] > 4.5:
        score -= 0.15
    if genes['sl_atr_mult'] < 1.5:
        score -= 0.1
    if genes['min_confidence'] < 0.52:
        score -= 0.05
    if genes['risk_percent'] > 0.30:
        score -= 0.1

    return score

# =========================================================
# DATA PREPARATION (unchanged except incremental improvements)
# =========================================================

def prepare_ticks_for_ga():
    print("📥 Fetching 2023‑2025 H1 data from MT5 for GA...")
    if not mt5.initialize():
        print("❌ MT5 not running")
        return {}

    ai = RealAITrader()
    cached = {}
    feature_cols = FEATURE_COLUMNS

    for pair in PAIRS:
        symbol = None
        for suffix in ['', 'm', '.', 'pro']:
            if mt5.symbol_select(pair + suffix, True):
                symbol = pair + suffix
                break
        if not symbol:
            print(f"❌ {pair}: symbol not found")
            continue

        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1,
                                     pd.to_datetime("2023-01-01"),
                                     datetime.now())
        if rates is None or len(rates) < 500:
            print(f"❌ {pair}: not enough H1 data")
            continue

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()

        spread_val = SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY
        df['spread_pct'] = (spread_val / df['close']) * 100

        df = ai.add_indicators(df)
        if df is None or len(df) < 500:
            print(f"⚠️  {pair}: insufficient indicator data")
            continue

        h4_close = df['close'].resample('4h').last()
        h4_close_prev = h4_close.shift(1)
        h4_ema200 = h4_close_prev.ewm(span=200, min_periods=200).mean()
        df['h4_ema200'] = h4_ema200.reindex(df.index, method='ffill')
        df['h4_uptrend']   = (df['close'] > df['h4_ema200']).astype(int)
        df['h4_downtrend'] = (df['close'] < df['h4_ema200']).astype(int)
        # H4 trend dummies
        df['h4_uptrend']   = (df['close'] > df['h4_ema200']).astype(int)
        df['h4_downtrend'] = (df['close'] < df['h4_ema200']).astype(int)

        # Asian session
        df['asian'] = ((hours >= 0) & (hours < 7)).astype(int)

        # Continuous volatility percentile
        df['atr_percentile'] = df['atr'].rolling(200).rank(pct=True)

        hours = df.index.hour
        df['london'] = ((hours >= 7) & (hours < 12)).astype(int)
        df['newyork'] = ((hours >= 13) & (hours < 18)).astype(int)

        atr_long = df['atr'].rolling(200).median()
        df['vol_high'] = (df['atr'] > atr_long * 1.5).astype(int)

        model = ai.models.get(pair)
        if model is None:
            print(f"⚠️  {pair}: no ML model")
            continue

        X = df[feature_cols].fillna(0)
        preds = model.predict(X)
        proba = model.predict_proba(X)
        df['ml_signal'] = preds
        df['ml_conf'] = np.where(preds == 1, proba[:, 1], proba[:, 0])

        df['h4_uptrend'] = df['close'] > df['h4_ema200']
        df['h4_downtrend'] = df['close'] < df['h4_ema200']
        df[['h4_uptrend', 'h4_downtrend']] = df[['h4_uptrend', 'h4_downtrend']].fillna(False)

        df = df.dropna()
        cached[pair] = df
        print(f"✅ {pair}: {len(df)} bars loaded from MT5")

    return cached

# =========================================================
# PAIR‑SPECIFIC REGIME MAPS (unchanged)
# =========================================================

def build_regime_maps():
    print("📊 Building pair‑specific regime maps...")
    if not mt5.initialize():
        print("❌ MT5 re‑init failed")
        return {}

    regime_maps = {}
    for pair in PAIRS:
        symbol = None
        for suffix in ['', 'm', '.', 'pro']:
            if mt5.symbol_select(pair + suffix, True):
                symbol = pair + suffix
                break
        if not symbol:
            continue

        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1,
                                     pd.to_datetime("2022-01-01"),
                                     datetime.now())
        if rates is None or len(rates) < 150:
            continue

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)

        high = df['high']
        low = df['low']
        close = df['close']

        tr = pd.concat([high - low,
                        (high - close.shift()).abs(),
                        (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        atr_pct = (atr / close) * 100

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm[plus_dm < minus_dm] = 0
        minus_dm[minus_dm < plus_dm] = 0
        atr_smooth = tr.rolling(14).mean()
        plus_di = 100 * plus_dm.rolling(14).mean() / atr_smooth
        minus_di = 100 * minus_dm.rolling(14).mean() / atr_smooth
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(14).mean()

        df = df.iloc[100:].copy()
        adx = adx.iloc[100:]
        atr_pct = atr_pct.iloc[100:]

        trend_thr = adx.quantile(0.65)
        range_thr = adx.quantile(0.35)
        vol_thr = atr_pct.quantile(0.75)

        regimes = []
        for a, v in zip(adx, atr_pct):
            if a >= trend_thr:
                regimes.append("trending")
            elif a <= range_thr and v < vol_thr:
                regimes.append("ranging")
            else:
                regimes.append("volatile")

        df['regime'] = regimes
        print(f"   {pair}: {df['regime'].value_counts().to_dict()}")
        regime_map = df['regime']
        regime_map.index = regime_map.index.floor('h')
        regime_maps[pair] = regime_map
        # Store thresholds in the map for later live use
        regime_maps[pair + '_thresholds'] = {
            'trend_thr': trend_thr,
            'range_thr': range_thr,
            'vol_thr': vol_thr
        }

    return regime_maps

# =========================================================
# GA EVOLUTION (now accepts regime_name and passes it)
# =========================================================

def evolve(cached, regime_name):
    population = [create_individual() for _ in range(POPULATION_SIZE)]
    best_genes = None
    best_score = -999999

    for gen in range(GENERATIONS):
        scores = [fitness_vectorized(ind, cached, regime_name) for ind in population]
        gen_best_idx = int(np.argmax(scores))
        if scores[gen_best_idx] > best_score:
            best_score = scores[gen_best_idx]
            best_genes = population[gen_best_idx].copy()
        print(f"  Gen {gen+1} | Best Score: {best_score:.4f}")

        next_population = []
        while len(next_population) < POPULATION_SIZE:
            p1 = select_tournament(population, scores)
            p2 = select_tournament(population, scores)
            child = {}
            for key in GENE_SPACE:
                if random.random() < CROSSOVER_RATE:
                    child[key] = p1[key]
                else:
                    child[key] = p2[key]
                if random.random() < MUTATION_RATE:
                    mn, mx, step = GENE_SPACE[key]
                    vals = np.arange(mn, mx + step / 2, step)
                    child[key] = float(round(random.choice(vals), 6))
            next_population.append(child)
        population = next_population

    return best_genes, best_score

# =========================================================
# MAIN (with trending override)
# =========================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧬 REGIME PARAM EVOLUTION (with filters + per‑pair)")
    print("=" * 60)

    cached_all = prepare_ticks_for_ga()
    if not cached_all:
        print("❌ No data loaded.")
        exit()

    regime_maps = build_regime_maps()
    if not regime_maps:
        print("❌ No regime maps built.")
        exit()

    subsets = {'trending': {}, 'ranging': {}, 'volatile': {}}
    for pair, df_tick in cached_all.items():
        if pair not in regime_maps:
            continue
        hour_index = df_tick.index.floor('h')
        df_tick['regime'] = hour_index.map(regime_maps[pair]).fillna('volatile')
        for regime in subsets.keys():
            sub = df_tick[df_tick['regime'] == regime]
            if len(sub) >= 500:
                subsets[regime][pair] = sub
                print(f"✅ {pair} {regime}: {len(sub)} bars")

    # ---- 5. Evolve each regime, then each pair independently ----
    regime_params = {}   # nested: pair -> regime -> genes, plus 'global' -> regime -> genes

    for regime in ['trending', 'ranging', 'volatile']:
        reg_cached = subsets[regime]
        if len(reg_cached) < 4:
            print(f"❌ Not enough data for {regime} (need ≥4 pairs) – skipping")
            continue

        # --- 5a. Global fallback for this regime ---
        print(f"\n🚀 EVOLVING REGIME‑LEVEL: {regime.upper()}")

        # Trending override (same as before)
        if regime == 'trending':
            orig_gene = GENE_SPACE.copy()
            GENE_SPACE['sl_atr_mult'] = (2.0, 3.5, 0.1)
            GENE_SPACE['tp_atr_mult'] = (3.0, 5.0, 0.2)
            GENE_SPACE['atr_max_non_jpy'] = (0.002, 0.008, 0.0005)

            global_genes, global_score = evolve(reg_cached, regime)
            GENE_SPACE = orig_gene
        else:
            global_genes, global_score = evolve(reg_cached, regime)

        print(f"🏆 {regime.upper()} global best score: {global_score:.4f}")
        print(json.dumps(global_genes, indent=4))

        # Store the global fallback
        if 'global' not in regime_params:
            regime_params['global'] = {}
        regime_params['global'][regime] = global_genes

        # --- 5b. Per‑pair evolution ---
        for pair in PAIRS:
            if pair not in reg_cached:
                continue
            pair_df = reg_cached[pair]   # single pair, single regime DataFrame
            if len(pair_df) < 500:
                continue

            print(f"   🔬 Evolve {pair} – {regime}...")
            try:
                # Trending override must be applied again for each pair
                if regime == 'trending':
                    orig_gene = GENE_SPACE.copy()
                    GENE_SPACE['sl_atr_mult'] = (2.0, 3.5, 0.1)
                    GENE_SPACE['tp_atr_mult'] = (3.0, 5.0, 0.2)
                    GENE_SPACE['atr_max_non_jpy'] = (0.002, 0.008, 0.0005)

                    pair_genes, pair_score = evolve({pair: pair_df}, regime)
                    GENE_SPACE = orig_gene
                else:
                    pair_genes, pair_score = evolve({pair: pair_df}, regime)

                if pair not in regime_params:
                    regime_params[pair] = {}
                regime_params[pair][regime] = pair_genes
                print(f"      ✅ {pair} {regime}: {pair_score:.4f}")
            except Exception as e:
                print(f"      ⚠️ {pair} failed: {e}")

    # ---- 6. Save into config.json under the 'Live' account ----
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    updated = False
    for acc in config.get('accounts', []):
        if acc.get('name') == 'Live':
            acc['regime_params'] = regime_params
            updated = True
            break
    if not updated:
        config['accounts'].append({
            "name": "Live",
            "regime_params": regime_params
        })

    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

    print("\n📲 Saved pair‑specific regime parameters to config.json")