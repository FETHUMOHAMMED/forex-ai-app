"""Validate the best FVG strategy with full statistical tests."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats
import json
from pathlib import Path

def validate_fvg_strategy():
    """Full validation of FVG_H4_2.5R_London strategy."""
    print("="*60)
    print("  VALIDATION: FVG H4 2.5R London")
    print("="*60)
    
    if not mt5.initialize():
        print("MT5 initialization failed")
        return None
    
    # Download full history
    print("\nDownloading 8-year history...")
    rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 10000)
    
    if rates is None:
        print("Failed to download data")
        mt5.shutdown()
        return None
    
    data = pd.DataFrame(rates)
    data['timestamp'] = pd.to_datetime(data['time'], unit='s')
    
    print(f"Data: {len(data)} bars from {data['timestamp'].min()} to {data['timestamp'].max()}")
    
    # Calculate indicators
    data['ema_50'] = data['close'].ewm(span=50).mean()
    data['ema_200'] = data['close'].ewm(span=200).mean()
    
    # ATR
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr'] = tr.rolling(14).mean()
    
    # Session filter
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    data['london_session'] = (data['hour'] >= 7) & (data['hour'] <= 11)
    
    # Generate trades
    trades = []
    
    for i in range(200, len(data)):
        if not data['london_session'].iloc[i]:
            continue
        
        # HTF bias
        bullish_bias = data['ema_50'].iloc[i] > data['ema_200'].iloc[i]
        
        # FVG detection
        if i >= 2:
            if bullish_bias and data['high'].iloc[i-2] < data['low'].iloc[i]:
                # Bullish FVG
                entry = data['close'].iloc[i]
                sl = entry - (data['atr'].iloc[i] * 1.5)
                tp = entry + (data['atr'].iloc[i] * 3.75)  # 2.5R
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        trades.append({
                            "r": -1, "result": "SL",
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
                        break
                    elif data['high'].iloc[j] >= tp:
                        trades.append({
                            "r": 2.5, "result": "TP",
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry) / (entry - sl)
                    trades.append({
                        "r": r, "result": "TIMEOUT",
                        "year": data['timestamp'].iloc[i].year,
                        "month": data['timestamp'].iloc[i].month
                    })
            
            elif not bullish_bias and data['low'].iloc[i-2] > data['high'].iloc[i]:
                # Bearish FVG
                entry = data['close'].iloc[i]
                sl = entry + (data['atr'].iloc[i] * 1.5)
                tp = entry - (data['atr'].iloc[i] * 3.75)
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['high'].iloc[j] >= sl:
                        trades.append({
                            "r": -1, "result": "SL",
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
                        break
                    elif data['low'].iloc[j] <= tp:
                        trades.append({
                            "r": 2.5, "result": "TP",
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (entry - exit_price) / (sl - entry)
                    trades.append({
                        "r": r, "result": "TIMEOUT",
                        "year": data['timestamp'].iloc[i].year,
                        "month": data['timestamp'].iloc[i].month
                    })
    
    mt5.shutdown()
    
    if not trades:
        print("No trades generated")
        return None
    
    trades_df = pd.DataFrame(trades)
    
    # Comprehensive validation
    print(f"\n{'='*60}")
    print("  COMPREHENSIVE VALIDATION RESULTS")
    print(f"{'='*60}")
    
    # 1. Basic stats
    wins = (trades_df['r'] > 0).sum()
    total = len(trades_df)
    win_rate = wins / total * 100
    gross_profit = trades_df[trades_df['r'] > 0]['r'].sum()
    gross_loss = abs(trades_df[trades_df['r'] < 0]['r'].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    expectancy = trades_df['r'].mean()
    
    print(f"\nBasic Statistics:")
    print(f"  Trades: {total}")
    print(f"  Win rate: {win_rate:.1f}%")
    print(f"  Profit factor: {pf:.3f}")
    print(f"  Expectancy: {expectancy:.3f}R")
    print(f"  Total R: {trades_df['r'].sum():.1f}")
    
    # 2. Statistical significance
    t_stat, p_value = stats.ttest_1samp(trades_df['r'], 0)
    
    print(f"\nStatistical Significance:")
    print(f"  T-statistic: {t_stat:.3f}")
    print(f"  P-value: {p_value:.4f}")
    print(f"  Significant at 95%: {'YES ?' if p_value < 0.05 else 'NO ?'}")
    
    # 3. Yearly consistency
    print(f"\nYearly Performance:")
    yearly = trades_df.groupby('year').agg({'r': ['sum', 'count']})
    for year, row in yearly.iterrows():
        status = "?" if row['r']['sum'] > 0 else "?"
        print(f"  {year}: {row['r']['sum']:.1f}R in {row['r']['count']} trades ({status})")
    
    # 4. Drawdown analysis
    cumulative = trades_df['r'].cumsum()
    running_max = cumulative.cummax()
    drawdown = cumulative - running_max
    max_dd = drawdown.min()
    
    print(f"\nRisk Metrics:")
    print(f"  Max drawdown: {max_dd:.1f}R")
    print(f"  Final equity: {cumulative.iloc[-1]:.1f}R")
    
    # 5. Out-of-sample test
    split_idx = int(len(trades_df) * 0.7)
    train = trades_df.iloc[:split_idx]
    test = trades_df.iloc[split_idx:]
    
    train_pf = train[train['r'] > 0]['r'].sum() / abs(train[train['r'] < 0]['r'].sum()) if train[train['r'] < 0]['r'].sum() != 0 else float('inf')
    test_pf = test[test['r'] > 0]['r'].sum() / abs(test[test['r'] < 0]['r'].sum()) if test[test['r'] < 0]['r'].sum() != 0 else float('inf')
    
    print(f"\nOut-of-Sample Test (70/30 split):")
    print(f"  Train: {len(train)} trades, PF {train_pf:.3f}, Exp {train['r'].mean():.3f}R")
    print(f"  Test: {len(test)} trades, PF {test_pf:.3f}, Exp {test['r'].mean():.3f}R")
    
    # 6. Monte Carlo simulation
    n_sims = 10000
    final_equities = []
    max_drawdowns = []
    
    np.random.seed(42)
    for _ in range(n_sims):
        shuffled = trades_df['r'].sample(frac=1).values
        equity = np.cumsum(shuffled)
        final_equities.append(equity[-1])
        
        running_max = np.maximum.accumulate(equity)
        dd = running_max - equity
        max_drawdowns.append(np.max(dd))
    
    prob_profit = (np.array(final_equities) > 0).mean() * 100
    ci_lower = np.percentile(final_equities, 5)
    ci_upper = np.percentile(final_equities, 95)
    
    print(f"\nMonte Carlo Simulation (10,000 runs):")
    print(f"  Probability of profit: {prob_profit:.1f}%")
    print(f"  90% CI for final equity: [{ci_lower:.1f}R, {ci_upper:.1f}R]")
    print(f"  Mean max drawdown: {np.mean(max_drawdowns):.1f}R")
    print(f"  95th percentile max DD: {np.percentile(max_drawdowns, 95):.1f}R")
    
    # 7. Final verdict
    print(f"\n{'='*60}")
    print("  FINAL VERDICT")
    print(f"{'='*60}")
    
    criteria_met = []
    if p_value < 0.05:
        criteria_met.append("? Statistically significant")
    if pf > 1.3:
        criteria_met.append("? Profit factor > 1.3")
    if expectancy > 0.2:
        criteria_met.append("? Expectancy > 0.2R")
    if prob_profit > 80:
        criteria_met.append("? Monte Carlo > 80% profitable")
    if test_pf > 1.2:
        criteria_met.append("? Out-of-sample PF > 1.2")
    
    if len(criteria_met) >= 4:
        print("  STRATEGY VALIDATED - PROCEED TO FORWARD TESTING")
    else:
        print("  STRATEGY NEEDS MORE VALIDATION")
    
    for criterion in criteria_met:
        print(f"    {criterion}")
    
    return trades_df

if __name__ == "__main__":
    trades = validate_fvg_strategy()
