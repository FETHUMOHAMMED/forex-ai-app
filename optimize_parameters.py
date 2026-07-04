"""
PARAMETER OPTIMIZATION (MT5 Historical Data – FAST)
Pre‑fetches hourly MT5 data for all pairs once, then tests 100 combinations offline.
"""

import os
import sys
import json
import itertools
import warnings
from datetime import datetime
import pandas as pd
import MetaTrader5 as mt5
from multi_backtest import PortfolioBacktest, SinglePairBacktest

warnings.filterwarnings('ignore')

# ========== CONFIGURATION ==========
PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
         'USDCHF', 'NZDUSD', 'USDSGD']
START_DATE = '2020-01-01'      # MT5 has data since 2020
END_DATE = '2025-01-01'
CAPITAL_PER_PAIR = 2000

PARAM_GRID = {
    'min_confidence': [0.50, 0.55, 0.60, 0.65],
    'risk_percent': [0.5, 1.0, 1.5, 2.0],
    'trail_atr_mult': [0.5, 1.0, 1.5, 2.0],
    'atr_min_non_jpy': [0.0002, 0.0003, 0.0005, 0.0007],
    'atr_max_non_jpy': [0.0025, 0.0030, 0.0035, 0.0040],
    'atr_min_jpy': [0.03, 0.04, 0.05, 0.06],
    'atr_max_jpy': [0.25, 0.30, 0.35, 0.40],
    'use_filters': [True]
}

LIMIT_COMBINATIONS = 100

def generate_param_combinations(param_grid, limit=None):
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = list(itertools.product(*values))
    if limit and len(combinations) > limit:
        step = len(combinations) // limit
        combinations = combinations[::step][:limit]
    return [dict(zip(keys, combo)) for combo in combinations]

def pre_download_mt5_data(pairs, start, end):
    """Fetch hourly bars from MT5 for all pairs and return dict {pair: DataFrame}."""
    if not mt5.initialize():
        print("❌ MT5 not running. Please open MetaTrader 5 and try again.")
        sys.exit(1)
    data = {}
    for pair in pairs:
        print(f"⬇️  Fetching {pair} from MT5...")
        # Temporary backtest instance just to access symbol detection
        bt = SinglePairBacktest(pair, start, end, 2000, 1, 1, 0.55, True)
        df = bt.fetch_data()
        if df is not None and len(df) > 100:
            data[pair] = df
            print(f"   ✅ {pair} – {len(df)} bars")
        else:
            print(f"   ❌ {pair} – no data")
    return data

def run_optimization():
    print("="*70)
    print("🔧 PARAMETER OPTIMIZATION (MT5 Hourly Data)")
    print(f"Pairs: {', '.join(PAIRS)}")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Capital per pair: ${CAPITAL_PER_PAIR}")
    print("="*70)

    # Step 1 – Download everything once
    cached_data = pre_download_mt5_data(PAIRS, START_DATE, END_DATE)
    if not cached_data:
        print("❌ No MT5 data downloaded. Aborting.")
        return
    print(f"\n✅ Data for {len(cached_data)} pairs cached. Starting optimization...\n")

    combinations = generate_param_combinations(PARAM_GRID, LIMIT_COMBINATIONS)
    print(f"Testing {len(combinations)} parameter combinations...\n")

    results = []
    best_score = -float('inf')

    for idx, params in enumerate(combinations, 1):
        print(f"\n--- Combination {idx}/{len(combinations)} ---")
        bt = PortfolioBacktest(
            pairs=PAIRS,
            start_date=START_DATE,
            end_date=END_DATE,
            initial_capital_per_pair=CAPITAL_PER_PAIR,
            risk_percent=params['risk_percent'],
            trail_atr_mult=params['trail_atr_mult'],
            min_confidence=params['min_confidence'],
            use_filters=params['use_filters'],
            atr_min_non_jpy=params['atr_min_non_jpy'],
            atr_max_non_jpy=params['atr_max_non_jpy'],
            atr_min_jpy=params['atr_min_jpy'],
            atr_max_jpy=params['atr_max_jpy'],
            preloaded_data_dict=cached_data   # <-- cached MT5 data
        )
        metrics = bt.run()
        if metrics:
            pf = metrics.get('profit_factor', 0) or 0
            dd = abs(metrics.get('max_drawdown', 0)) / 100
            wr = (metrics.get('win_rate', 0) or 0) / 100
            score = pf * (1 - dd) * wr

            result = {
                **params,
                'total_return': metrics.get('total_return', 0),
                'total_trades': metrics.get('total_trades', 0),
                'win_rate': metrics.get('win_rate', 0),
                'profit_factor': metrics.get('profit_factor', 0),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'total_pnl': metrics.get('total_pnl', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'composite_score': score
            }
            results.append(result)
            print(f"   Return: {result['total_return']:.2f}% | WR: {result['win_rate']:.1f}% | PF: {result['profit_factor']:.2f} | DD: {result['max_drawdown']:.2f}%")
            if score > best_score:
                best_score = score
        else:
            print("   ⚠️ Backtest failed (no trades)")

    if results:
        df = pd.DataFrame(results)
        df = df.sort_values('composite_score', ascending=False)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = f"optimization_results_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        print(f"\n✅ Results saved to {csv_path}")
        print("\n" + "="*70)
        print("🏆 TOP 5 PARAMETER SETS")
        print("="*70)
        for i, (_, row) in enumerate(df.head(5).iterrows()):
            print(f"\n#{i+1} Score: {row['composite_score']:.4f}")
            print(f"   Confidence: {row['min_confidence']:.0%} | Risk: {row['risk_percent']:.1f}% | Trail ATR: {row['trail_atr_mult']:.1f}")
            print(f"   ATR Non-JPY: {row['atr_min_non_jpy']:.5f}-{row['atr_max_non_jpy']:.5f} | ATR JPY: {row['atr_min_jpy']:.2f}-{row['atr_max_jpy']:.2f}")
            print(f"   Return: {row['total_return']:.2f}% | WR: {row['win_rate']:.1f}% | PF: {row['profit_factor']:.2f} | DD: {row['max_drawdown']:.2f}%")
    else:
        print("❌ No successful backtests.")

if __name__ == "__main__":
    run_optimization()