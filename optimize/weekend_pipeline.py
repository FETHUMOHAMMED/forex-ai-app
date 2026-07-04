"""
FULL WEEKEND AUTOMATION PIPELINE
1. Download fresh tick data from MT5 (last 4 months)
2. Evolve best GA parameters on 1‑minute tick data
3. Validate evolved parameters on 2‑year hourly data via walk‑forward
4. If average out‑of‑sample score > 0.4:
   – update the Live account in config.json with the evolved parameters
   – send Telegram confirmation
5. Otherwise send Telegram warning and keep current config
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
TICK_CSV_DIR = "data"
CONFIG_PATH = "config.json"
TARGET_ACCOUNT = "Live"

# GA settings (fast, for automation)
POPULATION_SIZE = 16
GENERATIONS_GA = 8
MUTATION_RATE = 0.2
CROSSOVER_RATE = 0.7

# Walk‑forward settings (quick validation on hourly data)
TRAIN_MONTHS = 6
TEST_MONTHS  = 2
STEP_MONTHS  = 2
GENERATIONS_WF = 3
POPULATION_WF  = 10

# Trading costs
SPREAD_NON_JPY = 0.0002
SPREAD_JPY    = 0.02
COMMISSION    = 7.0
INITIAL_CAPITAL = 2000

# Gene space
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

THRESHOLD_SCORE = 0.4   # minimum average out‑of‑sample score to accept

# ---- Step 1: Download fresh tick data ----
def download_fresh_ticks():
    print("⬇️  Step 1/4: Downloading fresh tick data …")
    if not mt5.initialize():
        print("❌ MT5 not running."); return False
    END = datetime.now()
    START = END - timedelta(days=120)

    for pair in PAIRS:
        # ═══════════════════════════════════════════════════════════
        # Optional: skip download if a recent CSV already exists
        # ═══════════════════════════════════════════════════════════
        filename = os.path.join(TICK_CSV_DIR, f"{pair}_ticks.csv")
        if os.path.exists(filename):
            file_age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(filename))).days
            if file_age < 5:
                print(f"   ⚪ {pair} – recent data exists (skipping download)")
                continue
        # ═══════════════════════════════════════════════════════════

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
            df.to_csv(filename)
            print(f"   ✅ {pair} – {len(df)} ticks saved")
        else:
            print(f"   ❌ No tick data for {pair}")

    mt5.shutdown()
    return True

# ---- Fitness function (vectorized) ----
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

# ---- Step 2: Prepare tick data for GA ----
def prepare_ticks_for_ga():
    print("🧮 Step 2/4: Loading tick data & precomputing ML …")
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
        model = ai.models.get(pair)
        if model is not None:
            feat_cols = ['rsi','macd','macd_signal','atr','volume_ratio',
                         'bb_upper','bb_lower','fvg_buy','fvg_sell',
                         'ob_buy','ob_sell','returns','high_low_ratio',
                         'bb_buy','bb_sell','lv_buy','lv_sell','mss_buy','mss_sell']
            X = ohlc[feat_cols].fillna(0).values
            preds = model.predict(X)
            probs = model.predict_proba(X)
        else:
            preds = np.zeros(len(ohlc), dtype=int)
            probs = np.ones((len(ohlc), 2)) * 0.5
        ohlc = ohlc.copy()
        ohlc['ml_signal'] = preds
        ohlc['ml_conf'] = np.where(preds==1, probs[:,1], probs[:,0])
        cached[pair] = ohlc
        print(f"   ✅ {pair} – {len(ohlc)} bars ready")
    return ai, cached

# ---- Step 3: Run GA on tick data ----
def run_ga(cached):
    print("🧬 Step 3/4: Evolving GA best parameters …")
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

    pop = [create_individual() for _ in range(POPULATION_SIZE)]
    best_score = -9999
    best_genes = None
    for gen in range(GENERATIONS_GA):
        scores = [fitness_vectorized(ind, cached) for ind in pop]
        idx_best = scores.index(max(scores))
        if scores[idx_best] > best_score:
            best_score = scores[idx_best]; best_genes = pop[idx_best].copy()
        new_pop = [pop[idx_best].copy()]   # elitism
        while len(new_pop) < POPULATION_SIZE:
            p1 = select_tournament(pop, scores)
            p2 = select_tournament(pop, scores)
            child = {k: (p1[k] if random.random()<CROSSOVER_RATE else p2[k]) for k in p1}
            if random.random() < MUTATION_RATE:
                k = random.choice(list(GENE_SPACE.keys()))
                mi, ma, st = GENE_SPACE[k]
                possible = np.arange(mi, ma+st/2, st)
                child[k] = float(random.choice(possible))
            new_pop.append(child)
        pop = new_pop
        print(f"   GA Gen {gen+1}/{GENERATIONS_GA}: Best {best_score:.4f}")
    print(f"🎯 Best GA Score: {best_score:.4f}")
    return best_genes

# ---- Step 4: Walk‑forward validation on hourly data ----
def run_walk_forward(genes):
    print("🔬 Step 4/4: Walk‑forward validation …")
    if not mt5.initialize():
        print("❌ MT5 not running for walk‑forward."); return -9999

    ai = RealAITrader()
    cached_hourly = {}
    for pair in PAIRS:
        symbol = None
        for suffix in ['', 'm', '.', 'pro']:
            if mt5.symbol_select(pair+suffix, True):
                symbol = pair+suffix
                break
        if not symbol:
            print(f"   ❌ Symbol not found for {pair}")
            continue
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1,
                                     pd.to_datetime('2023-01-01'),
                                     pd.to_datetime('2025-01-01'))
        if rates is None or len(rates) < 100:
            continue
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume':'volume'}, inplace=True)
        df = df[['open','high','low','close','volume']]
        df = ai.add_indicators(df)
        if df is None or len(df) < 100:
            continue
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
            preds = np.zeros(len(df), dtype=int)
            probs = np.ones((len(df), 2)) * 0.5
        df = df.copy()
        df['ml_signal'] = preds
        df['ml_conf'] = np.where(preds==1, probs[:,1], probs[:,0])
        cached_hourly[pair] = df
        print(f"   ✅ {pair} – {len(df)} bars")

    mt5.shutdown()

    results = []
    current = pd.to_datetime('2024-01-01')
    end = pd.to_datetime('2025-01-01')
    while current + pd.DateOffset(months=TEST_MONTHS) <= end:
        test_end = current + pd.DateOffset(months=TEST_MONTHS)
        test_cache = {}
        for pair, df in cached_hourly.items():
            edf = df[(df.index >= current) & (df.index < test_end)]
            if len(edf) > 100:
                test_cache[pair] = edf
        if len(test_cache) >= 4:
            score = fitness_vectorized(genes, test_cache) if genes else -9999
            results.append(score)
            print(f"   {current.date()} → {test_end.date()}  score: {score:.4f}")
        current += pd.DateOffset(months=TEST_MONTHS)

    avg = np.mean(results) if results else -9999
    print(f"📈 Average out‑of‑sample score: {avg:.4f}")
    return avg

# ---- Telegram notification ----
def send_telegram(msg):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id   = os.getenv('TELEGRAM_CHAT_ID')
    if bot_token and chat_id:
        notifier = TelegramNotifier(bot_token, chat_id)
        notifier.send_message(msg)
        print("📲 Telegram notification sent.")
    else:
        print("⚠️ Telegram credentials missing – no notification sent.")

# ---- Update config.json ----
def update_live_config(genes):
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    updated = False
    for acc in config.get('accounts', []):
        if acc.get('name') == TARGET_ACCOUNT:
            acc['min_confidence'] = genes['min_confidence']
            acc['risk_percent'] = genes['risk_percent']
            acc['atr_min_non_jpy'] = genes['atr_min_non_jpy']
            acc['atr_max_non_jpy'] = genes['atr_max_non_jpy']
            acc['atr_min_jpy'] = genes['atr_min_jpy']
            acc['atr_max_jpy'] = genes['atr_max_jpy']
            print(f"✅ Updated {TARGET_ACCOUNT} account with evolved parameters.")
            updated = True
            break
    if not updated:
        print(f"⚠️ Target account '{TARGET_ACCOUNT}' not found in config.")
        return
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

# ---- Main pipeline ----
def main():
    print("="*60)
    print("🚀 WEEKEND AUTOMATION PIPELINE STARTED")
    print("="*60)

    # Step 1
    if not download_fresh_ticks():
        send_telegram("❌ Weekend pipeline failed: tick download error.")
        return

    # Step 2
    ai, cached_ga = prepare_ticks_for_ga()
    if not cached_ga:
        send_telegram("❌ Weekend pipeline failed: no data for GA.")
        return

    # Step 3
    best_genes = run_ga(cached_ga)
    if not best_genes:
        send_telegram("❌ Weekend pipeline failed: GA did not converge.")
        return

    # Step 4
    avg_score = run_walk_forward(best_genes)
    if avg_score > THRESHOLD_SCORE:
        update_live_config(best_genes)
        send_telegram(
            f"✅ Weekend pipeline successful!\n"
            f"Avg out‑of‑sample score: {avg_score:.4f}\n"
            f"Live account updated with evolved parameters."
        )
    else:
        send_telegram(
            f"⚠️ Weekend pipeline completed, but out‑of‑sample score ({avg_score:.4f}) below threshold.\n"
            f"Live config NOT updated. Keeping current parameters."
        )

    print("\n✅ Weekend pipeline finished.")

if __name__ == "__main__":
    main()