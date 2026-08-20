"""Final validation with proper statistical tests."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from datetime import datetime
import json

def run_final_validation():
    """Run complete validation with all statistical tests."""
    print("="*60)
    print("  FINAL VALIDATION - COMPLETE STATISTICAL ANALYSIS")
    print("="*60)
    
    # Download data
    if not mt5.initialize():
        print("MT5 init failed")
        return None
    
    rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 10000)
    mt5.shutdown()
    
    if rates is None:
        print("No data")
        return None
    
    data = pd.DataFrame(rates)
    data['timestamp'] = pd.to_datetime(data['time'], unit='s')
    
    # Calculate indicators
    data['ema_50'] = data['close'].ewm(span=50).mean()
    data['ema_200'] = data['close'].ewm(span=200).mean()
    
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr'] = tr.rolling(14).mean()
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    
    # Run strategy with validated parameters
    trades = []
    
    for i in range(200, len(data)):
        if not (7 <= data['hour'].iloc[i] <= 11):
            continue
        
        bullish_bias = data['ema_50'].iloc[i] > data['ema_200'].iloc[i]
        
        if i >= 2:
            if bullish_bias and data['high'].iloc[i-2] < data['low'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry - (data['atr'].iloc[i] * 2.0)
                tp = entry + (data['atr'].iloc[i] * 5.0)
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        trades.append({"r": -1, "year": data['timestamp'].iloc[i].year})
                        break
                    elif data['high'].iloc[j] >= tp:
                        trades.append({"r": 2.5, "year": data['timestamp'].iloc[i].year})
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry) / (entry - sl)
                    trades.append({"r": r, "year": data['timestamp'].iloc[i].year})
            
            elif not bullish_bias and data['low'].iloc[i-2] > data['high'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry + (data['atr'].iloc[i] * 2.0)
                tp = entry - (data['atr'].iloc[i] * 5.0)
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['high'].iloc[j] >= sl:
                        trades.append({"r": -1, "year": data['timestamp'].iloc[i].year})
                        break
                    elif data['low'].iloc[j] <= tp:
                        trades.append({"r": 2.5, "year": data['timestamp'].iloc[i].year})
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (entry - exit_price) / (sl - entry)
                    trades.append({"r": r, "year": data['timestamp'].iloc[i].year})
    
    # Comprehensive statistics
    trades_df = pd.DataFrame(trades)
    r_values = trades_df['r'].values
    
    # Basic stats
    total = len(r_values)
    wins = sum(1 for r in r_values if r > 0)
    win_rate = wins / total
    gross_profit = sum(r for r in r_values if r > 0)
    gross_loss = abs(sum(r for r in r_values if r < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    expectancy = np.mean(r_values)
    std_dev = np.std(r_values)
    
    # Statistical significance
    t_stat, p_value = scipy_stats.ttest_1samp(r_values, 0)
    
    # Sharpe ratio
    sharpe = expectancy / std_dev if std_dev > 0 else 0
    
    # Drawdown
    cumulative = np.cumsum(r_values)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max
    max_dd = np.min(drawdown)
    
    # Print results
    print(f"\nComplete Statistics:")
    print(f"  Total trades: {total}")
    print(f"  Win rate: {win_rate*100:.1f}%")
    print(f"  Profit factor: {pf:.3f}")
    print(f"  Expectancy: {expectancy:.3f}R")
    print(f"  Std deviation: {std_dev:.3f}R")
    print(f"  Sharpe ratio: {sharpe:.3f}")
    print(f"  Max drawdown: {max_dd:.1f}R")
    print(f"  Total R: {sum(r_values):.1f}")
    
    print(f"\nStatistical Tests:")
    print(f"  T-statistic: {t_stat:.3f}")
    print(f"  P-value: {p_value:.4f}")
    print(f"  Significant at 95%: {'YES ?' if p_value < 0.05 else 'NO ?'}")
    print(f"  Significant at 99%: {'YES ?' if p_value < 0.01 else 'NO ?'}")
    
    # Yearly breakdown
    print(f"\nYearly Performance:")
    yearly = trades_df.groupby('year')['r'].agg(['sum', 'count', 'mean'])
    for year, row in yearly.iterrows():
        status = "?" if row['sum'] > 0 else "?"
        print(f"  {year}: {row['sum']:.1f}R in {row['count']} trades ({status})")
    
    # Monte Carlo
    n_sims = 10000
    np.random.seed(42)
    final_equities = []
    max_drawdowns = []
    
    for _ in range(n_sims):
        shuffled = np.random.permutation(r_values)
        equity = np.cumsum(shuffled)
        final_equities.append(equity[-1])
        
        running_max = np.maximum.accumulate(equity)
        dd = running_max - equity
        max_drawdowns.append(np.max(dd))
    
    prob_profit = (np.array(final_equities) > 0).mean() * 100
    
    print(f"\nMonte Carlo Simulation (10,000 runs):")
    print(f"  Probability of profit: {prob_profit:.1f}%")
    print(f"  Mean final equity: {np.mean(final_equities):.1f}R")
    print(f"  5th percentile: {np.percentile(final_equities, 5):.1f}R")
    print(f"  95th percentile: {np.percentile(final_equities, 95):.1f}R")
    print(f"  Mean max DD: {np.mean(max_drawdowns):.1f}R")
    print(f"  95th percentile max DD: {np.percentile(max_drawdowns, 95):.1f}R")
    
    # Final verdict
    print(f"\n{'='*60}")
    print("  FINAL VERDICT")
    print("="*60)
    
    checks = [
        (p_value < 0.05, "Statistical significance (p < 0.05)"),
        (pf > 1.3, "Profit factor > 1.3"),
        (expectancy > 0.2, "Expectancy > 0.2R"),
        (sharpe > 0.5, "Sharpe ratio > 0.5"),
        (max_dd > -15, "Max drawdown < 15R"),
        (prob_profit > 80, "Monte Carlo > 80% profitable"),
        (total >= 30, "Minimum 30 trades")
    ]
    
    passed = sum(1 for check, _ in checks if check)
    total_checks = len(checks)
    
    print(f"\n  Passed {passed}/{total_checks} criteria")
    
    for check, description in checks:
        status = "?" if check else "?"
        print(f"    {status} {description}")
    
    if passed >= 6:
        print(f"\n  STRATEGY FULLY VALIDATED")
        print(f"  Ready for forward testing and eventual live deployment")
    elif passed >= 4:
        print(f"\n  STRATEGY MOSTLY VALIDATED")
        print(f"  Forward testing recommended to confirm")
    else:
        print(f"\n  STRATEGY NEEDS IMPROVEMENT")
        print(f"  Return to research phase")
    
    return trades_df

if __name__ == "__main__":
    results = run_final_validation()
