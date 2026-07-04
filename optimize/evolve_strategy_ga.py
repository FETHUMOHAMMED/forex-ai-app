"""
Genetic Algorithm Strategy Evolution – Evolves trading strategies on tick data.
Uses your RealAITrader indicator pipeline and vectorized trade simulation.
"""

import os, sys, json, time, random
import numpy as np
import pandas as pd
from datetime import datetime
from real_ai_service import RealAITrader
import MetaTrader5 as mt5

# ---------- CONFIG ----------
PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'USDSGD']
START_DATE = '2024-01-01'
END_DATE   = '2025-01-01'
INITIAL_CAPITAL = 2000
SPREAD_NON_JPY = 0.0002
SPREAD_JPY    = 0.02
COMMISSION    = 7.0

POPULATION_SIZE = 20
GENERATIONS = 10
MUTATION_RATE = 0.2
CROSSOVER_RATE = 0.7
ELITE_SIZE = 2

# ---------- GENE DEFINITIONS ----------
# Each gene is a (min, max, step) tuple for uniform random init
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

# ---------- DATA LOADING ----------
def fetch_mt5(pair, start, end):
    """Get hourly bars from MT5 (just like your existing backtest)."""
    for suffix in ['', 'm', '.', 'pro']:
        sym = pair + suffix
        if mt5.symbol_select(sym, True):
            symbol = sym
            break
    else:
        return None
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1,
                                 pd.to_datetime(start), pd.to_datetime(end))
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    return df[['open', 'high', 'low', 'close', 'volume']]

# ---------- TRADE SIMULATION (Fast, Vectorized) ----------
def simulate_trade_vectorized(df, entry_idx, signal, sl, tp, lot, pair):
    spread_price = SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY
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
        pnl -= spread_price * lot * 100000
    else:
        pnl = (entry_price - exit_price) * lot * 100000
        pnl -= spread_price * lot * 100000
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
    return max(0.01, min(round(lot, 2), 10.0))

# ---------- INDIVIDUAL (Strategy) ----------
def create_individual():
    """Randomly create a gene set within the defined space."""
    genes = {}
    for key, (min_val, max_val, step) in GENE_SPACE.items():
        # Choose a random value from the discrete set of possible values
        possible = np.arange(min_val, max_val + step/2, step)
        genes[key] = float(round(random.choice(possible), 6))
    return genes

def fitness(genes, cached_data, ai):
    """Evaluate a strategy on all pairs and return the fitness score (Profit Factor × Win Rate/100)."""
    all_trades = []
    for pair, df in cached_data.items():
        # Precompute ATR
        atr = (df['high'] - df['low']).rolling(14).mean()
        # Signal generation: use ICT patterns + ML confidence
        # Precompute ML signals (same as your existing tick backtest)
        model = ai.models.get(pair)
        if model is not None:
            feature_cols = [
                'rsi','macd','macd_signal','atr','volume_ratio',
                'bb_upper','bb_lower','fvg_buy','fvg_sell',
                'ob_buy','ob_sell','returns','high_low_ratio',
                'bb_buy','bb_sell','lv_buy','lv_sell','mss_buy','mss_sell'
            ]
            X = df[feature_cols].fillna(0).values
            preds = model.predict(X)
            probs = model.predict_proba(X)
            df['ml_signal'] = preds
            df['ml_conf'] = np.where(preds==1, probs[:,1], probs[:,0])
        else:
            df['ml_signal'] = 0
            df['ml_conf'] = 0.5

        balance = INITIAL_CAPITAL
        i = 100
        while i < len(df)-1:
            row = df.iloc[i]
            a = atr.iloc[i]
            if pd.isna(a): i += 1; continue
            # ATR filter using genes
            if 'JPY' in pair:
                if a < genes['atr_min_jpy'] or a > genes['atr_max_jpy']: i += 1; continue
            else:
                if a < genes['atr_min_non_jpy'] or a > genes['atr_max_non_jpy']: i += 1; continue

            # ICT signals
            ict_b = bool(row['fvg_buy'] or row['ob_buy'] or row['bb_buy'] or row['lv_buy'] or row['mss_buy'])
            ict_s = bool(row['fvg_sell'] or row['ob_sell'] or row['bb_sell'] or row['lv_sell'] or row['mss_sell'])
            ml_pred = int(row['ml_signal'])
            mc = row['ml_conf']

            signal = None
            conf_val = 0.5
            if ict_b and ml_pred == 1 and mc > 0.55:
                signal = 'BUY'; conf_val = mc
            elif ict_s and ml_pred == 0 and mc > 0.55:
                signal = 'SELL'; conf_val = mc
            elif mc > 0.65:
                signal = 'BUY' if ml_pred == 1 else 'SELL'; conf_val = mc
            elif ict_b and mc > 0.51:
                signal = 'BUY'; conf_val = 0.55
            elif ict_s and mc > 0.51:
                signal = 'SELL'; conf_val = 0.55
            elif mc > 0.51:
                signal = 'BUY' if ml_pred == 1 else 'SELL'; conf_val = mc

            if not signal or conf_val < genes['min_confidence']:
                i += 1; continue

            entry = row['close']
            sl_mult = genes['sl_atr_mult']
            tp_mult = genes['tp_atr_mult']
            if signal == 'BUY':
                sl = entry - a * sl_mult
                tp = entry + a * tp_mult
            else:
                sl = entry + a * sl_mult
                tp = entry - a * tp_mult

            lot = calc_lot(balance, entry, sl, genes['risk_percent'], pair)
            ei, ep, pnl, _ = simulate_trade_vectorized(df, i, signal, sl, tp, lot, pair)
            balance += pnl
            all_trades.append(pnl)
            i = ei + 1

    if not all_trades:
        return -9999
    arr = np.array(all_trades)
    wins = np.sum(arr > 0)
    total = len(arr)
    gross_profit = arr[arr > 0].sum()
    gross_loss = abs(arr[arr < 0].sum())
    pf = gross_profit / gross_loss if gross_loss else float('inf')
    wr = wins / total * 100 if total else 0
    score = pf * (wr / 100)
    return score

def select_tournament(population, scores, k=3):
    """Select one individual using tournament selection."""
    indices = random.sample(range(len(population)), k)
    best_idx = max(indices, key=lambda i: scores[i])
    return population[best_idx].copy()

def crossover(parent1, parent2):
    """Uniform crossover on the genes."""
    child = {}
    for key in parent1.keys():
        child[key] = parent1[key] if random.random() < 0.5 else parent2[key]
    return child

def mutate(genes, rate):
    """Mutate genes with a certain probability by randomizing them within the defined space."""
    for key, (min_val, max_val, step) in GENE_SPACE.items():
        if random.random() < rate:
            possible = np.arange(min_val, max_val + step/2, step)
            genes[key] = float(round(random.choice(possible), 6))
    return genes

def main():
    print("="*60)
    print("🧬 GENETIC ALGORITHM STRATEGY EVOLUTION")
    print("="*60)

    if not mt5.initialize():
        print("❌ MT5 not running."); sys.exit(1)

    # Load AI and data (once)
    ai = RealAITrader()
    cached = {}
    for pair in PAIRS:
        print(f"⬇️  Fetching {pair} …")
        df = fetch_mt5(pair, START_DATE, END_DATE)
        if df is not None and len(df) > 100:
            df = ai.add_indicators(df)
            if df is not None and len(df) > 100:
                cached[pair] = df
                print(f"   ✅ {pair} – {len(df)} bars")
        if pair not in cached:
            print(f"   ❌ {pair} – skipped")

    if not cached:
        print("No data."); sys.exit(1)

    # Initialize population
    population = [create_individual() for _ in range(POPULATION_SIZE)]
    best_score_all_time = -9999
    best_genes_all_time = None

    for gen in range(GENERATIONS):
        t0 = time.time()
        # Evaluate
        scores = [fitness(ind, cached, ai) for ind in population]
        gen_best = max(scores)
        gen_best_idx = scores.index(gen_best)
        gen_best_genes = population[gen_best_idx]
        if gen_best > best_score_all_time:
            best_score_all_time = gen_best
            best_genes_all_time = gen_best_genes.copy()

        print(f"\n🏆 Gen {gen+1}/{GENERATIONS} – Best Score: {gen_best:.4f} | Avg Score: {np.mean(scores):.4f} | ⏱️ {time.time()-t0:.1f}s")
        print(f"   Best Genes: {gen_best_genes}")

        # Selection and reproduction
        new_population = []
        # Elitism: keep the best
        new_population.append(gen_best_genes.copy())
        for _ in range(POPULATION_SIZE - 1):
            parent1 = select_tournament(population, scores)
            parent2 = select_tournament(population, scores)
            if random.random() < CROSSOVER_RATE:
                child = crossover(parent1, parent2)
            else:
                child = parent1.copy()
            child = mutate(child, MUTATION_RATE)
            new_population.append(child)
        population = new_population

    # Final report
    print("\n" + "="*60)
    print("🎉 EVOLUTION COMPLETE – Best Strategy Found")
    print("="*60)
    print(f"Fitness: {best_score_all_time:.4f}")
    print(json.dumps(best_genes_all_time, indent=2))
    # Save to file
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = f"ga_best_genes_{ts}.json"
    with open(json_path, 'w') as f:
        json.dump(best_genes_all_time, f, indent=2)
    print(f"✅ Saved to {json_path}")

    # Optionally apply to your config? We'll leave that manual for safety.

if __name__ == "__main__":
    main()