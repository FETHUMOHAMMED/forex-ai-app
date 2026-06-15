"""
validate_oos.py – Regime‑separated OOS validation with full diagnostic.
Uses the new signal logic: ICT + ML + H4 trend filter, no pure‑ML fallback.
"""

import json
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime


from evolve_regime_params import (
    prepare_ticks_for_ga,    # loads tick cache (now with H4 columns)
    build_regime_maps,       # pair‑specific hourly regime maps
    fitness_vectorized,      # we'll reuse the composite score as reference
    fast_exit_scan,
    INITIAL_CAPITAL,
    SPREAD_JPY, SPREAD_NON_JPY, COMMISSION,
    PAIRS
)

# ======================== helper: full backtest ========================
def detailed_regime_backtest(genes, cached_reg, regime_name=""):
    """
    Run the exact signal logic from the new fitness_vectorized,
    collect all PnLs, and print the full dashboard.
    """
    all_pnls = []

    for pair, df in cached_reg.items():
        close   = df['close'].values.astype(np.float64)
        high    = df['high'].values.astype(np.float64)
        low     = df['low'].values.astype(np.float64)
        atr     = df['atr'].values.astype(np.float64)
        ml_sig  = df['ml_signal'].values.astype(np.int32)
        ml_conf = df['ml_conf'].values.astype(np.float64)

        # H4 trend columns (added by prepare_ticks_for_ga)
        h4_up   = df['h4_uptrend'].values.astype(bool)
        h4_down = df['h4_downtrend'].values.astype(bool)

        ict_buy = (df['fvg_buy'] | df['ob_buy'] | df['bb_buy'] |
                   df['lv_buy'] | df['mss_buy']).values.astype(bool)
        ict_sell = (df['fvg_sell'] | df['ob_sell'] | df['bb_sell'] |
                    df['lv_sell'] | df['mss_sell']).values.astype(bool)

        spread_price = SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY
        n = len(close)

        # ATR filter
        if 'JPY' in pair:
            atr_ok = (atr >= genes['atr_min_jpy']) & (atr <= genes['atr_max_jpy'])
        else:
            atr_ok = (atr >= genes['atr_min_non_jpy']) & (atr <= genes['atr_max_non_jpy'])

        # Signal logic (exactly matches new fitness_vectorized)
        buy_signal = (
            atr_ok &
            ict_buy &
            (ml_sig == 1) &
            (ml_conf >= genes['min_confidence']) &
            h4_up
        )
        sell_signal = (
            atr_ok &
            ict_sell &
            (ml_sig == 0) &
            (ml_conf >= genes['min_confidence']) &
            h4_down
        )

        signal_mask = buy_signal | sell_signal
        if not signal_mask.any():
            continue

        entry_idx = np.where(signal_mask)[0]
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
        lots = np.clip(np.round(lots, 2), 0.01, 5.0)   # max 5 lots as in new code

        # Exit scan
        signals_int = np.where(signals == 'BUY', 1, 0).astype(np.int64)
        exit_idxs, exit_prices = fast_exit_scan(
            entry_idx.astype(np.int64), signals_int,
            high, low, close, sls, tps, n
        )

        # PnL
        pnls = np.where(signals == 'BUY',
                        (exit_prices - entry_prices) * lots * 100_000,
                        (entry_prices - exit_prices) * lots * 100_000)
        pnls -= spread_price * lots * 100_000
        pnls -= lots * COMMISSION
        if 'JPY' in pair:
            pnls /= exit_prices

        all_pnls.extend(pnls.tolist())

    # ---------------------- metrics ----------------------
    if not all_pnls:
        print(f"\n{'='*20} {regime_name.upper()} {'='*20}")
        print("  No trades generated.")
        return None

    arr = np.array(all_pnls)
    wins = np.sum(arr > 0)
    total = len(arr)
    gp = arr[arr > 0].sum()
    gl = abs(arr[arr < 0].sum())
    pf = gp / gl if gl else 10.0
    wr = wins / total
    avg_trade = arr.mean()
    equity = np.cumsum(arr)
    max_dd = np.min(equity - np.maximum.accumulate(equity))
    sharpe = arr.mean() / (arr.std() + 1e-9)

    # ---- composite score (same as new fitness, just for reference) ----
    composite = (
        pf * 0.35 +
        wr * 0.20 +
        (avg_trade / 20) * 0.20 +
        sharpe * 0.15 +
        (min(total / 500, 1.0) * 0.10)
    )
    composite -= abs(max_dd) / 1500
    if pf < 1.05: composite -= 1.0
    if wr < 0.45: composite -= 0.5
    if avg_trade <= 0: composite -= 1.0

    print(f"\n{'='*20} {regime_name.upper()} {'='*20}")
    print(f"  Trades         : {total}")
    print(f"  Win Rate       : {wr*100:.1f}%")
    print(f"  Profit Factor  : {pf:.2f}")
    print(f"  Expectancy     : {avg_trade:.2f}")
    print(f"  Max DD         : {max_dd:.2f}")
    print(f"  Net Profit     : {arr.sum():.2f}")
    print(f"  Sharpe‑like    : {sharpe:.2f}")
    print(f"  Composite Score: {composite:.2f}")

    return {
        "trades": total, "win_rate": wr*100, "profit_factor": pf,
        "expectancy": avg_trade, "max_dd": max_dd,
        "net_profit": arr.sum(), "sharpe_like": sharpe, "composite": composite
    }

def confidence_bin_analysis(pnls, confidences, regime_name=""):
    """Print win rate & expectancy for each confidence bin."""
    bins = [0.50, 0.55, 0.60, 0.65, 0.70, 0.85]
    labels = ["0.50-0.55", "0.55-0.60", "0.60-0.65", "0.65-0.70", "0.70+"]
    df = pd.DataFrame({'pnl': pnls, 'conf': confidences})
    df['bin'] = pd.cut(df['conf'], bins=bins, labels=labels, include_lowest=True)
    
    print(f"\n--- Confidence Bin Analysis ({regime_name}) ---")
    for bin_name, group in df.groupby('bin', observed=False):
        if len(group) == 0:
            continue
        wr = (group['pnl'] > 0).mean()
        expectancy = group['pnl'].mean()
        print(f"  Bin {bin_name}: trades={len(group)}, WR={wr:.1%}, expectancy={expectancy:.2f}")
# =========================== MAIN ============================
if __name__ == "__main__":
    # ---- 1. Load evolved parameters ----
    with open('config.json') as f:
        config = json.load(f)

    regime_params = None
    for acc in config['accounts']:
        if acc['name'] == 'Live':
            regime_params = acc['regime_params']
            break
    if regime_params is None:
        raise RuntimeError("No 'Live' account with regime_params in config.json")

    # ---- 2. Load tick cache (with H4 columns) ----
    cached_all = prepare_ticks_for_ga()

    # ---- 3. Build pair‑specific regime maps (needs MT5) ----
    regime_maps = build_regime_maps()
    if not regime_maps:
        raise RuntimeError("Failed to build regime maps. Is MT5 running?")

    # ---- 4. Assign regime labels to every bar ----
    for pair, df in cached_all.items():
        if pair not in regime_maps:
            continue
        hour_index = df.index.floor('h')
        df['regime'] = hour_index.map(regime_maps[pair]).fillna('volatile')

    # ---- 5. Validate each regime only on its own data ----
    for regime in ['trending', 'ranging', 'volatile']:
        if isinstance(regime_params, dict) and 'global' in regime_params:
            genes = regime_params['global'][regime]
        else:
            genes = regime_params[regime]
        if genes is None:
            print(f"Regime '{regime}' not found in config. Skipping.")
            continue

        regime_cache = {}
        for pair, df in cached_all.items():
            sub_df = df[df['regime'] == regime]
            if len(sub_df) >= 500:
                regime_cache[pair] = sub_df

        if len(regime_cache) < 4:
            print(f"Regime {regime}: not enough data – skipping")
            continue

        detailed_regime_backtest(genes, regime_cache, regime)

    print("\n✅ OOS regime‑separated validation complete.")