import os
import json
import itertools
import pandas as pd
import MetaTrader5 as mt5                     # <-- this was missing
from datetime import datetime
from backtest.data_loader import MT5DataLoader
from backtest.execution import ExecutionEngine
from backtest.engine import BacktestEngine
from real_ai_service import RealAITrader

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.json')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

def run_parameter_grid(pairs, start, end, param_grid, limit=100):
    loader = MT5DataLoader()
    exec_eng = ExecutionEngine(spread_non_jpy=CONFIG.get('backtest_spread_non_jpy', 0.0002),
                               spread_jpy=CONFIG.get('backtest_spread_jpy', 0.02),
                               commission=CONFIG.get('backtest_commission_per_lot', 7.0))
    ai = RealAITrader()
    engine = BacktestEngine(ai, exec_eng)

    # Pre-fetch data for all pairs
    cached = {}
    for pair in pairs:
        df = loader.get_data(pair, mt5.TIMEFRAME_H1, start, end)   # <-- now works
        if df is not None:
            cached[pair] = df
    if not cached:
        print("❌ No data fetched.")
        return

    keys = list(param_grid.keys())
    values = list(param_grid.values())
    all_combos = list(itertools.product(*values))
    if limit and len(all_combos) > limit:
        step = len(all_combos) // limit
        all_combos = all_combos[::step][:limit]

    results = []
    for combo in all_combos:
        params = dict(zip(keys, combo))
        print(f"Testing: {params}")
        all_trades = []
        for pair in pairs:
            trades = engine.run(cached[pair], pair, initial_balance=2000,
                                risk_percent=params['risk_percent'],
                                min_confidence=params['min_confidence'],
                                use_filters=True,
                                atr_min=params['atr_min_non_jpy'],
                                atr_max=params['atr_max_non_jpy'],
                                atr_min_jpy=params['atr_min_jpy'],
                                atr_max_jpy=params['atr_max_jpy'])
            all_trades.extend(trades)

        if not all_trades:
            continue

        df_trades = pd.DataFrame(all_trades)
        wins = len(df_trades[df_trades['pnl'] > 0])
        total = len(df_trades)
        total_pnl = df_trades['pnl'].sum()
        gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        pf = gross_profit / gross_loss if gross_loss else float('inf')
        win_rate = (wins / total) * 100 if total else 0

        score = pf * (1 - abs(min(0, total_pnl/2000))/100) * (win_rate/100)

        results.append({**params, 'score': score, 'total_pnl': total_pnl, 'win_rate': win_rate, 'pf': pf})

    if results:
        df_res = pd.DataFrame(results).sort_values('score', ascending=False)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = f"optimization_results_{timestamp}.csv"
        df_res.to_csv(csv_path, index=False)
        print(f"\n✅ Results saved to {csv_path}")
        print(df_res.head())
    else:
        print("❌ No successful backtests.")

if __name__ == '__main__':
    PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'USDSGD']
    START = '2020-01-01'
    END = '2025-01-01'
    PARAM_GRID = {
        'min_confidence': [0.50, 0.55, 0.60, 0.65],
        'risk_percent': [0.5, 1.0, 1.5, 2.0],
        'atr_min_non_jpy': [0.0002, 0.0003, 0.0005, 0.0007],
        'atr_max_non_jpy': [0.0025, 0.0030, 0.0035, 0.0040],
        'atr_min_jpy': [0.03, 0.04, 0.05, 0.06],
        'atr_max_jpy': [0.25, 0.30, 0.35, 0.40]
    }
    run_parameter_grid(PAIRS, START, END, PARAM_GRID, limit=100)