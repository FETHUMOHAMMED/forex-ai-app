"""USDJPY H4 Strategy - Based on empirical trend evidence."""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

def run_usdjpy_h4_strategy():
    """Trade USDJPY trend on H4 timeframe."""
    print("="*60)
    print("  USDJPY H4 TREND STRATEGY")
    print("="*60)
    
    # Load data
    with open('data/research/mt5_historical_data.pkl', 'rb') as f:
        all_data = pickle.load(f)
    
    data = all_data['USDJPYm']['H4'].copy()
    
    print(f"\nData: {len(data)} H4 bars")
    print(f"Period: {data['timestamp'].min()} to {data['timestamp'].max()}")
    
    # Calculate indicators
    data['ema_20'] = data['close'].ewm(span=20, min_periods=20).mean()
    data['ema_50'] = data['close'].ewm(span=50, min_periods=50).mean()
    data['ema_200'] = data['close'].ewm(span=200, min_periods=200).mean()
    
    # ATR
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr'] = tr.rolling(window=14, min_periods=1).mean()
    
    # RSI
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # Generate signals
    trades = []
    
    for i in range(200, len(data)):
        # Long: Strong uptrend + pullback
        long_condition = (
            data['ema_20'].iloc[i] > data['ema_50'].iloc[i] > data['ema_200'].iloc[i] and
            data['close'].iloc[i] > data['ema_20'].iloc[i] and
            data['rsi'].iloc[i] < 50 and  # Not overbought
            data['close'].iloc[i] > data['close'].iloc[i-1]  # Momentum
        )
        
        # Short: Strong downtrend + rally
        short_condition = (
            data['ema_20'].iloc[i] < data['ema_50'].iloc[i] < data['ema_200'].iloc[i] and
            data['close'].iloc[i] < data['ema_20'].iloc[i] and
            data['rsi'].iloc[i] > 50 and  # Not oversold
            data['close'].iloc[i] < data['close'].iloc[i-1]  # Momentum
        )
        
        if long_condition:
            entry = data['close'].iloc[i]
            sl = entry - (data['atr'].iloc[i] * 2)
            tp = entry + (data['atr'].iloc[i] * 4)  # 2:1 R:R
            
            # Hold for 20 bars maximum (based on 20-bar analysis)
            exit_idx = min(i + 20, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trades.append({
                        "r": -1, "result": "SL",
                        "entry_time": data['timestamp'].iloc[i],
                        "exit_time": data['timestamp'].iloc[j]
                    })
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({
                        "r": 2, "result": "TP",
                        "entry_time": data['timestamp'].iloc[i],
                        "exit_time": data['timestamp'].iloc[j]
                    })
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (exit_price - entry) / (entry - sl)
                trades.append({
                    "r": r, "result": "TIMEOUT",
                    "entry_time": data['timestamp'].iloc[i],
                    "exit_time": data['timestamp'].iloc[exit_idx]
                })
        
        elif short_condition:
            entry = data['close'].iloc[i]
            sl = entry + (data['atr'].iloc[i] * 2)
            tp = entry - (data['atr'].iloc[i] * 4)
            
            exit_idx = min(i + 20, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['high'].iloc[j] >= sl:
                    trades.append({
                        "r": -1, "result": "SL",
                        "entry_time": data['timestamp'].iloc[i],
                        "exit_time": data['timestamp'].iloc[j]
                    })
                    break
                elif data['low'].iloc[j] <= tp:
                    trades.append({
                        "r": 2, "result": "TP",
                        "entry_time": data['timestamp'].iloc[i],
                        "exit_time": data['timestamp'].iloc[j]
                    })
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (entry - exit_price) / (sl - entry)
                trades.append({
                    "r": r, "result": "TIMEOUT",
                    "entry_time": data['timestamp'].iloc[i],
                    "exit_time": data['timestamp'].iloc[exit_idx]
                })
    
    # Results
    if trades:
        trades_df = pd.DataFrame(trades)
        
        wins = (trades_df['r'] > 0).sum()
        total = len(trades_df)
        win_rate = wins / total * 100
        
        gross_profit = trades_df[trades_df['r'] > 0]['r'].sum()
        gross_loss = abs(trades_df[trades_df['r'] < 0]['r'].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        expectancy = trades_df['r'].mean()
        
        print(f"\nResults:")
        print(f"  Total trades: {total}")
        print(f"  Win rate: {win_rate:.1f}%")
        print(f"  Profit factor: {pf:.3f}")
        print(f"  Expectancy: {expectancy:.3f}R")
        print(f"  Total R: {trades_df['r'].sum():.1f}")
        
        # Monthly analysis
        trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')
        monthly = trades_df.groupby('month').agg({
            'r': ['sum', 'count', 'mean']
        })
        
        print(f"\nMonthly Performance:")
        for month, row in monthly.iterrows():
            status = "?" if row['r']['sum'] > 0 else "?"
            print(f"  {month}: {row['r']['sum']:.1f}R in {row['r']['count']} trades ({status})")
        
        # Statistical significance
        from scipy import stats
        t_stat, p_value = stats.ttest_1samp(trades_df['r'], 0)
        
        print(f"\nStatistical Test:")
        print(f"  T-statistic: {t_stat:.3f}")
        print(f"  P-value: {p_value:.3f}")
        print(f"  Significant at 95%: {'YES' if p_value < 0.05 else 'NO'}")
        
        # Max drawdown
        cumulative = trades_df['r'].cumsum()
        running_max = cumulative.cummax()
        drawdown = cumulative - running_max
        max_dd = drawdown.min()
        
        print(f"\nRisk Metrics:")
        print(f"  Max drawdown: {max_dd:.1f}R")
        print(f"  Final equity: {cumulative.iloc[-1]:.1f}R")
        
        return trades_df
    
    return None

if __name__ == "__main__":
    trades = run_usdjpy_h4_strategy()
