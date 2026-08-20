"""Validate if AUDUSD 05:00 UTC edge is real or random."""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

def validate_edge():
    """Test if the AUDUSD edge is statistically significant."""
    print("="*60)
    print("  VALIDATION: Is the AUDUSD Edge Real?")
    print("="*60)
    
    # Load data
    with open('data/research/mt5_historical_data.pkl', 'rb') as f:
        all_data = pickle.load(f)
    
    data = all_data['AUDUSDm']['M15'].copy()
    
    # Add features
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    data['returns_50'] = data['close'].pct_change(50)
    data['returns_20'] = data['close'].pct_change(20)
    
    # ATR
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr'] = tr.rolling(window=14, min_periods=1).mean()
    
    # Run the strategy
    trades = []
    
    for i in range(100, len(data)):
        if data['hour'].iloc[i] != 5:
            continue
        
        if (data['returns_50'].iloc[i] > 0.001 and 
            data['returns_20'].iloc[i] < 0):
            
            entry = data['close'].iloc[i]
            atr = data['atr'].iloc[i]
            sl = entry - (atr * 2.0)  # Wider SL
            tp = entry + (atr * 5.0)  # 2.5:1 R:R
            
            exit_idx = min(i + 50, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trades.append({"r": -1, "result": "SL", "time": data['timestamp'].iloc[i]})
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({"r": 2.5, "result": "TP", "time": data['timestamp'].iloc[i]})
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (exit_price - entry) / (entry - sl)
                trades.append({"r": r, "result": "TIMEOUT", "time": data['timestamp'].iloc[i]})
        
        elif (data['returns_50'].iloc[i] < -0.001 and 
              data['returns_20'].iloc[i] > 0):
            
            entry = data['close'].iloc[i]
            atr = data['atr'].iloc[i]
            sl = entry + (atr * 2.0)
            tp = entry - (atr * 5.0)
            
            exit_idx = min(i + 50, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['high'].iloc[j] >= sl:
                    trades.append({"r": -1, "result": "SL", "time": data['timestamp'].iloc[i]})
                    break
                elif data['low'].iloc[j] <= tp:
                    trades.append({"r": 2.5, "result": "TP", "time": data['timestamp'].iloc[i]})
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (entry - exit_price) / (sl - entry)
                trades.append({"r": r, "result": "TIMEOUT", "time": data['timestamp'].iloc[i]})
    
    if not trades:
        print("No trades generated")
        return
    
    trades_df = pd.DataFrame(trades)
    
    # 1. Basic statistics
    print("\n1. BASIC STATISTICS")
    print(f"   Total trades: {len(trades_df)}")
    print(f"   Mean R: {trades_df['r'].mean():.3f}")
    print(f"   Std R: {trades_df['r'].std():.3f}")
    print(f"   Median R: {trades_df['r'].median():.3f}")
    
    # 2. Statistical significance test
    print("\n2. STATISTICAL SIGNIFICANCE")
    from scipy import stats
    
    t_stat, p_value = stats.ttest_1samp(trades_df['r'], 0)
    print(f"   T-statistic: {t_stat:.3f}")
    print(f"   P-value: {p_value:.3f}")
    print(f"   Significant at 95%: {'YES' if p_value < 0.05 else 'NO'}")
    print(f"   Significant at 90%: {'YES' if p_value < 0.10 else 'NO'}")
    
    # 3. Bootstrap confidence interval
    print("\n3. BOOTSTRAP CONFIDENCE INTERVAL")
    n_bootstrap = 10000
    bootstrap_means = []
    np.random.seed(42)
    
    for _ in range(n_bootstrap):
        sample = np.random.choice(trades_df['r'], size=len(trades_df), replace=True)
        bootstrap_means.append(sample.mean())
    
    ci_lower = np.percentile(bootstrap_means, 5)
    ci_upper = np.percentile(bootstrap_means, 95)
    
    print(f"   90% CI: [{ci_lower:.3f}, {ci_upper:.3f}]")
    print(f"   Probability of positive expectancy: {(np.array(bootstrap_means) > 0).mean()*100:.1f}%")
    
    # 4. Monte Carlo simulation
    print("\n4. MONTE CARLO SIMULATION")
    n_sims = 1000
    final_equities = []
    max_drawdowns = []
    
    for _ in range(n_sims):
        shuffled = trades_df['r'].sample(frac=1).values
        equity = np.cumsum(shuffled)
        final_equities.append(equity[-1])
        
        running_max = np.maximum.accumulate(equity)
        drawdown = running_max - equity
        max_drawdowns.append(np.max(drawdown))
    
    print(f"   Mean final equity: {np.mean(final_equities):.1f}R")
    print(f"   5th percentile: {np.percentile(final_equities, 5):.1f}R")
    print(f"   95th percentile: {np.percentile(final_equities, 95):.1f}R")
    print(f"   Probability of profit: {(np.array(final_equities) > 0).mean()*100:.1f}%")
    print(f"   Mean max drawdown: {np.mean(max_drawdowns):.1f}R")
    print(f"   95th percentile max DD: {np.percentile(max_drawdowns, 95):.1f}R")
    
    # 5. Monthly consistency
    print("\n5. MONTHLY CONSISTENCY")
    trades_df['month'] = pd.to_datetime(trades_df['time']).dt.to_period('M')
    
    monthly = trades_df.groupby('month')['r'].agg(['sum', 'count', 'mean'])
    for month, row in monthly.iterrows():
        status = "?" if row['sum'] > 0 else "?"
        print(f"   {month}: {row['sum']:.1f}R in {row['count']} trades ({status})")
    
    # 6. Worst-case scenario
    print("\n6. WORST-CASE ANALYSIS")
    sorted_r = trades_df['r'].sort_values().values
    worst_10 = sorted_r[:10]
    print(f"   Worst 10 trades: {worst_10.sum():.1f}R")
    print(f"   Worst single trade: {sorted_r[0]:.1f}R")
    
    # 7. Equity curve
    print("\n7. EQUITY CURVE ANALYSIS")
    trades_df['cumulative'] = trades_df['r'].cumsum()
    trades_df['drawdown'] = trades_df['cumulative'] - trades_df['cumulative'].cummax()
    
    print(f"   Final equity: {trades_df['cumulative'].iloc[-1]:.1f}R")
    print(f"   Max drawdown: {trades_df['drawdown'].min():.1f}R")
    print(f"   Current drawdown: {trades_df['drawdown'].iloc[-1]:.1f}R")
    
    # 8. Verdict
    print("\n" + "="*60)
    print("  VERDICT")
    print("="*60)
    
    if p_value < 0.05 and ci_lower > 0 and (np.array(bootstrap_means) > 0).mean() > 0.95:
        print("  ? STATISTICALLY SIGNIFICANT EDGE")
        print("  This edge appears real and robust")
        print("  Proceed to forward testing")
    elif p_value < 0.10 and ci_lower < 0:
        print("  ? MARGINAL EDGE")
        print("  Some evidence of edge but not conclusive")
        print("  Need more data or forward testing")
    else:
        print("  ? NO STATISTICALLY SIGNIFICANT EDGE")
        print("  The observed results could be random chance")
        print("  Do not deploy this strategy live")
    
    return trades_df

if __name__ == "__main__":
    trades = validate_edge()
