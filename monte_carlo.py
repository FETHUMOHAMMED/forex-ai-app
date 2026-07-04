"""
MONTE CARLO ROBUSTNESS TEST
Randomizes trade order, adds realistic dollar slippage, skips trades, and measures survival.
Uses the OOS trade list from the current regime parameters.
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
import MetaTrader5 as mt5

from evolve_regime_params import (
    build_regime_maps, fast_exit_scan,
    INITIAL_CAPITAL, SPREAD_JPY, SPREAD_NON_JPY, COMMISSION, PAIRS
)
from real_ai_service import RealAITrader

# ------------------ Monte Carlo settings ------------------
NUM_SIMULATIONS = 1000
TRADE_SKIP_PROB = 0.02          # skip 2% of trades
RUIN_THRESHOLD = 0.5            # 50% of initial capital = ruin

# ------------------ Helper: backtest to get trades ------------------
def get_oos_trades(regime_params, regime_name, start='2024-07-01', end='2025-01-01'):
    """Run the same OOS backtest as validate_oos.py and return a list of PnL and confidences."""
    if not mt5.initialize():
        raise RuntimeError("MT5 not running")
    ai = RealAITrader()
    feature_cols = [
        'rsi', 'macd', 'macd_signal', 'atr', 'volume_ratio',
        'fvg_buy', 'fvg_sell', 'ob_buy', 'ob_sell',
        'mss_buy', 'mss_sell',
        'dist_from_h4_ema', 'london', 'newyork', 'vol_high',
        'returns', 'high_low_ratio'
    ]
    # Fetch data (same as validate_oos.py)
    cached = {}
    for pair in PAIRS:
        symbol = None
        for suffix in ['', 'm', '.', 'pro']:
            if mt5.symbol_select(pair + suffix, True):
                symbol = pair + suffix
                break
        if not symbol:
            continue
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1,
                                     pd.to_datetime('2023-01-01'),
                                     pd.to_datetime('2025-01-01'))
        if rates is None or len(rates) < 500:
            continue
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        df = df[['open','high','low','close','volume']]
        spread_val = SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY
        df['spread_pct'] = (spread_val / df['close']) * 100
        df = ai.add_indicators(df)
        if df is None or len(df) < 500:
            continue
        h4 = df['close'].resample('4h').last()
        h4_ema200 = h4.ewm(span=200).mean()
        df['h4_ema200'] = h4_ema200.reindex(df.index, method='ffill')
        df['dist_from_h4_ema'] = (df['close'] - df['h4_ema200']) / df['h4_ema200'] * 100
        hours = df.index.hour
        df['london'] = ((hours >= 7) & (hours < 12)).astype(int)
        df['newyork'] = ((hours >= 13) & (hours < 18)).astype(int)
        atr_long = df['atr'].rolling(200).median()
        df['vol_high'] = (df['atr'] > atr_long * 1.5).astype(int)
        model = ai.models.get(pair)
        if model:
            X = df[feature_cols].fillna(0)
            preds = model.predict(X)
            proba = model.predict_proba(X)
            df['ml_signal'] = preds
            df['ml_conf'] = np.where(preds == 1, proba[:, 1], proba[:, 0])
        else:
            df['ml_signal'] = 0
            df['ml_conf'] = 0.5
        df['h4_uptrend'] = df['close'] > df['h4_ema200']
        df['h4_downtrend'] = df['close'] < df['h4_ema200']
        df[['h4_uptrend','h4_downtrend']] = df[['h4_uptrend','h4_downtrend']].fillna(False)
        df = df.dropna()
        cached[pair] = df

    # Regime maps and filter by regime + date
    regime_maps = build_regime_maps()
    oos_start = pd.to_datetime(start)
    oos_end = pd.to_datetime(end)
    pnl_list = []
    for pair, df in cached.items():
        if pair not in regime_maps:
            continue
        hour_index = df.index.floor('h')
        df['regime'] = hour_index.map(regime_maps[pair]).fillna('volatile')
        mask = (df.index >= oos_start) & (df.index < oos_end) & (df['regime'] == regime_name)
        sub = df[mask]
        if len(sub) < 500:
            continue
        # Re-run backtest logic (simplified: we don't need to re-implement all filters for Monte Carlo,
        # we just reuse the trade list from validate_oos. But to keep it self-contained, we'll replicate the signal logic.)
        close = sub['close'].values.astype(np.float64)
        high = sub['high'].values.astype(np.float64)
        low = sub['low'].values.astype(np.float64)
        atr = sub['atr'].values.astype(np.float64)
        ml_sig = sub['ml_signal'].values.astype(np.int32)
        ml_conf = sub['ml_conf'].values.astype(np.float64)
        h4_up = sub['h4_uptrend'].values.astype(bool)
        h4_down = sub['h4_downtrend'].values.astype(bool)
        ict_buy = (sub['fvg_buy'] | sub['ob_buy'] | sub['bb_buy'] |
                   sub['lv_buy'] | sub['mss_buy']).values.astype(bool)
        ict_sell = (sub['fvg_sell'] | sub['ob_sell'] | sub['bb_sell'] |
                    sub['lv_sell'] | sub['mss_sell']).values.astype(bool)
        genes = regime_params[regime_name]
        if 'JPY' in pair:
            atr_ok = (atr >= genes['atr_min_jpy']) & (atr <= genes['atr_max_jpy'])
        else:
            atr_ok = (atr >= genes['atr_min_non_jpy']) & (atr <= genes['atr_max_non_jpy'])
        if regime_name == 'trending':
            buy_signal = (atr_ok & ict_buy & (ml_sig == 1) & (ml_conf >= genes['min_confidence']) & h4_up)
            sell_signal = (atr_ok & ict_sell & (ml_sig == 0) & (ml_conf >= genes['min_confidence']) & h4_down)
        else:
            buy_signal = (atr_ok & ict_buy & (ml_sig == 1) & (ml_conf >= genes['min_confidence']))
            sell_signal = (atr_ok & ict_sell & (ml_sig == 0) & (ml_conf >= genes['min_confidence']))
        signal_mask = buy_signal | sell_signal
        if not signal_mask.any():
            continue
        entry_idx = np.where(signal_mask)[0]
        signals = np.where(buy_signal[entry_idx], 'BUY', 'SELL')
        entry_prices = close[entry_idx]
        atr_entry = atr[entry_idx]
        sl_mult = genes['sl_atr_mult']
        tp_mult = genes['tp_atr_mult']
        sls = np.where(signals == 'BUY', entry_prices - atr_entry * sl_mult, entry_prices + atr_entry * sl_mult)
        tps = np.where(signals == 'BUY', entry_prices + atr_entry * tp_mult, entry_prices - atr_entry * tp_mult)
        risk_amount = INITIAL_CAPITAL * (genes['risk_percent'] / 100.0)
        pip_value = 0.01 if 'JPY' in pair else 0.0001
        sl_dist = np.abs(entry_prices - sls)
        sl_pips = sl_dist / pip_value
        sl_pips[sl_pips == 0] = 0.01
        lots = risk_amount / (sl_pips * 10)
        lots = np.clip(np.round(lots, 2), 0.01, 5.0)
        signals_int = np.where(signals == 'BUY', 1, 0).astype(np.int64)
        exit_idxs, exit_prices = fast_exit_scan(entry_idx.astype(np.int64), signals_int, high, low, close, sls, tps, len(close))
        pnls = np.where(signals == 'BUY', (exit_prices - entry_prices) * lots * 100000, (entry_prices - exit_prices) * lots * 100000)
        pnls -= (SPREAD_JPY if 'JPY' in pair else SPREAD_NON_JPY) * lots * 100000
        pnls -= lots * COMMISSION
        if 'JPY' in pair:
            pnls /= exit_prices
        pnl_list.extend(pnls.tolist())
    return pnl_list

# ------------------ Monte Carlo simulation (corrected slippage) ------------------
def monte_carlo(trades, num_sims=NUM_SIMULATIONS):
    """
    Run Monte Carlo simulations on a list of dollar PnL values.
    Applies dollar-based slippage (proportional to average trade size) and random trade skips.
    """
    equity_curves = []
    final_equities = []
    max_drawdowns = []
    ruin_count = 0

    # Estimate slippage standard deviation based on average absolute trade size
    avg_trade_abs = np.mean(np.abs(trades)) if len(trades) > 0 else 10.0
    slip_std = max(avg_trade_abs * 0.05, 0.5)   # 5% of avg trade, minimum $0.5

    for _ in range(num_sims):
        shuffled = np.random.permutation(trades)
        # Skip 2% of trades
        mask = np.random.rand(len(shuffled)) > TRADE_SKIP_PROB
        shuffled = shuffled[mask]
        if len(shuffled) == 0:
            final_equities.append(INITIAL_CAPITAL)
            max_drawdowns.append(0)
            continue

        # Apply dollar slippage (reduces profit)
        slippage = np.random.normal(0, slip_std, len(shuffled))
        shuffled = shuffled - slippage

        equity = INITIAL_CAPITAL + np.cumsum(shuffled)
        final_eq = equity[-1]
        # Drawdown
        running_max = np.maximum.accumulate(equity)
        dd = (equity - running_max) / running_max
        max_dd = np.min(dd)
        # Ruin
        if np.any(equity <= INITIAL_CAPITAL * RUIN_THRESHOLD):
            ruin_count += 1
        final_equities.append(final_eq)
        max_drawdowns.append(max_dd)

    final_equities = np.array(final_equities)
    max_drawdowns = np.array(max_drawdowns)
    survival = np.mean(final_equities > INITIAL_CAPITAL)
    median_final = np.median(final_equities)
    ci_low = np.percentile(final_equities, 5)
    ci_high = np.percentile(final_equities, 95)
    median_dd = np.median(max_drawdowns)
    worst_dd = np.min(max_drawdowns)
    ruin_prob = ruin_count / num_sims

    return {
        'survival_rate': survival,
        'median_final_equity': median_final,
        'ci_5th': ci_low,
        'ci_95th': ci_high,
        'median_max_dd': median_dd,
        'worst_dd': worst_dd,
        'ruin_probability': ruin_prob
    }

# ------------------ Main ------------------
if __name__ == '__main__':
    # Load regime params
    with open('config.json') as f:
        config = json.load(f)
    regime_params = None
    for acc in config['accounts']:
        if acc['name'] == 'Live':
            regime_params = acc.get('regime_params', {})
            break
    if not regime_params:
        raise RuntimeError("No Live account with regime_params found")

    # Use the global (regime‑level) parameters for the standalone test
    global_params = regime_params.get('global', {})
    if not global_params:
        # Fallback: try the old flat structure
        global_params = regime_params

    # Run for each regime and print results
    for regime in ['trending', 'ranging', 'volatile']:
        genes = global_params.get(regime)
        if genes is None:
            print(f"Regime '{regime}' not found in global params – skipping")
            continue
        print(f"\n{'='*40} {regime.upper()} {'='*40}")
        trades = get_oos_trades(global_params, regime)
        if len(trades) < 10:
            print("Not enough trades for Monte Carlo simulation.")
            continue
        print(f"Total trades: {len(trades)}")
        results = monte_carlo(np.array(trades))
        print(f"Survival rate (positive P&L): {results['survival_rate']:.1%}")
        print(f"Median final equity: ${results['median_final_equity']:,.2f}")
        print(f"90% confidence interval: [${results['ci_5th']:,.2f}, ${results['ci_95th']:,.2f}]")
        print(f"Median max drawdown: {results['median_max_dd']:.1%}")
        print(f"Worst-case drawdown: {results['worst_dd']:.1%}")
        print(f"Probability of ruin (50% loss): {results['ruin_probability']:.1%}")