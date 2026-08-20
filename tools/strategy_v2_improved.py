"""Improved USDJPYm strategy with better filters."""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

def run_improved_strategy():
    """Run improved strategy with multiple filters."""
    print("="*60)
    print("  USDJPYm IMPROVED STRATEGY V2")
    print("="*60)
    
    # Load data
    with open('data/research/mt5_historical_data.pkl', 'rb') as f:
        all_data = pickle.load(f)
    
    data = all_data['USDJPYm']['M5'].copy()
    
    # Calculate indicators
    print("\nCalculating indicators...")
    
    # Trend indicators
    data['ema_20'] = data['close'].ewm(span=20, min_periods=20).mean()
    data['ema_50'] = data['close'].ewm(span=50, min_periods=50).mean()
    data['ema_200'] = data['close'].ewm(span=200, min_periods=200).mean()
    data['ema_slope'] = data['ema_50'].diff(10)  # Trend strength
    
    # Volatility
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr'] = tr.rolling(window=14, min_periods=1).mean()
    data['atr_pct'] = data['atr'] / data['close']  # Normalized ATR
    
    # Momentum
    data['rsi'] = 100 - (100 / (1 + (
        data['close'].diff().where(data['close'].diff() > 0, 0).rolling(14).mean() /
        (-data['close'].diff().where(data['close'].diff() < 0, 0)).rolling(14).mean()
    )))
    
    # Session
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    data['in_session'] = ((data['hour'] >= 7) & (data['hour'] <= 16)).astype(int)
    
    # Volume (if available)
    if 'tick_volume' in data.columns:
        data['volume_ma'] = data['tick_volume'].rolling(20).mean()
        data['volume_ratio'] = data['tick_volume'] / data['volume_ma']
    else:
        data['volume_ratio'] = 1.0
    
    # Generate signals with multiple filters
    print("\nGenerating improved signals...")
    trades = []
    
    for i in range(200, len(data)):
        # Skip if not in session
        if not data['in_session'].iloc[i]:
            continue
        
        # Strong trend filter
        trend_strength = abs(data['ema_slope'].iloc[i]) / data['close'].iloc[i]
        strong_trend = trend_strength > 0.0001  # Minimum trend strength
        
        # Volatility filter (avoid too volatile or too quiet)
        vol_ok = 0.0005 < data['atr_pct'].iloc[i] < 0.003
        
        # Volume filter (higher volume = better)
        volume_ok = data['volume_ratio'].iloc[i] > 0.8
        
        if not (strong_trend and vol_ok and volume_ok):
            continue
        
        # Long conditions
        long_signal = (
            data['ema_20'].iloc[i] > data['ema_50'].iloc[i] > data['ema_200'].iloc[i] and
            data['close'].iloc[i] > data['ema_20'].iloc[i] and
            data['rsi'].iloc[i] < 45 and  # Pullback in uptrend
            data['ema_slope'].iloc[i] > 0  # Rising trend
        )
        
        # Short conditions
        short_signal = (
            data['ema_20'].iloc[i] < data['ema_50'].iloc[i] < data['ema_200'].iloc[i] and
            data['close'].iloc[i] < data['ema_20'].iloc[i] and
            data['rsi'].iloc[i] > 55 and  # Rally in downtrend
            data['ema_slope'].iloc[i] < 0  # Falling trend
        )
        
        if long_signal:
            entry = data['close'].iloc[i]
            atr = data['atr'].iloc[i]
            sl = entry - (atr * 1.2)
            tp = entry + (atr * 2.4)  # 2:1 R:R
            
            # Track trade
            for j in range(i+1, min(i+300, len(data))):
                if data['low'].iloc[j] <= sl:
                    trades.append({
                        "direction": "LONG",
                        "result": "LOSS",
                        "r": -1,
                        "entry_time": data['timestamp'].iloc[i],
                        "exit_time": data['timestamp'].iloc[j],
                        "bars_held": j - i
                    })
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({
                        "direction": "LONG",
                        "result": "WIN",
                        "r": 2,
                        "entry_time": data['timestamp'].iloc[i],
                        "exit_time": data['timestamp'].iloc[j],
                        "bars_held": j - i
                    })
                    break
            else:
                exit_price = data['close'].iloc[min(i+300, len(data)-1)]
                r = (exit_price - entry) / (entry - sl)
                trades.append({
                    "direction": "LONG",
                    "result": "TIMEOUT",
                    "r": r,
                    "entry_time": data['timestamp'].iloc[i],
                    "exit_time": data['timestamp'].iloc[min(i+300, len(data)-1)],
                    "bars_held": 300
                })
        
        elif short_signal:
            entry = data['close'].iloc[i]
            atr = data['atr'].iloc[i]
            sl = entry + (atr * 1.2)
            tp = entry - (atr * 2.4)
            
            for j in range(i+1, min(i+300, len(data))):
                if data['high'].iloc[j] >= sl:
                    trades.append({
                        "direction": "SHORT",
                        "result": "LOSS",
                        "r": -1,
                        "entry_time": data['timestamp'].iloc[i],
                        "exit_time": data['timestamp'].iloc[j],
                        "bars_held": j - i
                    })
                    break
                elif data['low'].iloc[j] <= tp:
                    trades.append({
                        "direction": "SHORT",
                        "result": "WIN",
                        "r": 2,
                        "entry_time": data['timestamp'].iloc[i],
                        "exit_time": data['timestamp'].iloc[j],
                        "bars_held": j - i
                    })
                    break
            else:
                exit_price = data['close'].iloc[min(i+300, len(data)-1)]
                r = (entry - exit_price) / (sl - entry)
                trades.append({
                    "direction": "SHORT",
                    "result": "TIMEOUT",
                    "r": r,
                    "entry_time": data['timestamp'].iloc[i],
                    "exit_time": data['timestamp'].iloc[min(i+300, len(data)-1)],
                    "bars_held": 300
                })
    
    # Analysis
    print(f"\nGenerated {len(trades)} trades")
    
    if trades:
        trades_df = pd.DataFrame(trades)
        
        # Basic stats
        wins = sum(trades_df['result'] == 'WIN')
        losses = sum(trades_df['result'] == 'LOSS')
        timeouts = sum(trades_df['result'] == 'TIMEOUT')
        
        gross_profit = trades_df[trades_df['r'] > 0]['r'].sum()
        gross_loss = abs(trades_df[trades_df['r'] < 0]['r'].sum())
        
        r_values = trades_df['r'].values
        cumulative = np.cumsum(r_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # By direction
        long_trades = trades_df[trades_df['direction'] == 'LONG']
        short_trades = trades_df[trades_df['direction'] == 'SHORT']
        
        # Print results
        print("\n" + "="*60)
        print("  IMPROVED STRATEGY RESULTS")
        print("="*60)
        print(f"  Total trades: {len(trades)}")
        print(f"  Win rate: {wins/len(trades)*100:.1f}%")
        print(f"  Profit factor: {gross_profit/gross_loss:.3f}")
        print(f"  Expectancy: {np.mean(r_values):.3f}R")
        print(f"  Total R: {sum(r_values):.1f}")
        print(f"  Max drawdown: {max_drawdown:.1f}R")
        print(f"  Avg bars held: {trades_df['bars_held'].mean():.1f}")
        print(f"\n  Long trades: {len(long_trades)} ({(long_trades['result']=='WIN').mean()*100:.1f}% win)")
        print(f"  Short trades: {len(short_trades)} ({(short_trades['result']=='WIN').mean()*100:.1f}% win)")
        
        # Monthly breakdown
        trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')
        monthly = trades_df.groupby('month').agg({
            'r': ['sum', 'count'],
            'result': lambda x: (x == 'WIN').mean()
        })
        
        print("\n  Monthly performance:")
        for month, row in monthly.iterrows():
            print(f"    {month}: {row['r']['sum']:.1f}R in {row['r']['count']} trades ({row['result']:.0%} win)")
        
        return trades_df
    
    return None

if __name__ == "__main__":
    trades = run_improved_strategy()
