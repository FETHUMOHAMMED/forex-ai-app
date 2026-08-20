"""Strategy based on actual data analysis findings."""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

def run_data_driven_strategy():
    """Strategy using only empirically validated patterns."""
    print("="*60)
    print("  DATA-DRIVEN STRATEGY")
    print("  Based on actual market analysis")
    print("="*60)
    
    # Load data
    with open('data/research/mt5_historical_data.pkl', 'rb') as f:
        all_data = pickle.load(f)
    
    data = all_data['USDJPYm']['M15'].copy()
    
    print(f"\nData: {len(data)} bars")
    
    # Key finding: Longer timeframe momentum works (50-100 bars)
    # Best hours: 22:00, 19:00, 07:00, 05:00 UTC
    # Avoid: 20:00-21:00 UTC
    
    # Calculate features
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    data['returns_50'] = data['close'].pct_change(50)
    data['returns_20'] = data['close'].pct_change(20)
    
    # Generate signals only during good hours
    good_hours = [5, 7, 19, 22]
    data['good_hour'] = data['hour'].isin(good_hours)
    
    trades = []
    
    for i in range(100, len(data)):
        # Only trade during empirically good hours
        if not data['good_hour'].iloc[i]:
            continue
        
        # Long signal: 50-bar momentum positive + 20-bar pullback
        if data['returns_50'].iloc[i] > 0.001 and data['returns_20'].iloc[i] < 0:
            entry = data['close'].iloc[i]
            sl = entry * 0.998  # 0.2% stop
            # Target: hold for 50 bars (based on 50-bar analysis)
            
            # Simulate holding for 50 bars
            exit_idx = min(i + 50, len(data) - 1)
            exit_price = data['close'].iloc[exit_idx]
            
            r = (exit_price - entry) / (entry - sl)
            trades.append({
                "direction": "LONG",
                "r": r,
                "entry_time": data['timestamp'].iloc[i],
                "exit_time": data['timestamp'].iloc[exit_idx],
                "hour": data['hour'].iloc[i]
            })
        
        # Short signal: negative 50-bar momentum + 20-bar rally
        elif data['returns_50'].iloc[i] < -0.001 and data['returns_20'].iloc[i] > 0:
            entry = data['close'].iloc[i]
            sl = entry * 1.002  # 0.2% stop
            
            exit_idx = min(i + 50, len(data) - 1)
            exit_price = data['close'].iloc[exit_idx]
            
            r = (entry - exit_price) / (sl - entry)
            trades.append({
                "direction": "SHORT",
                "r": r,
                "entry_time": data['timestamp'].iloc[i],
                "exit_time": data['timestamp'].iloc[exit_idx],
                "hour": data['hour'].iloc[i]
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
        print(f"  Expectancy: {expectancy:.4f}R")
        
        # By hour
        print(f"\nBy hour:")
        for hour in good_hours:
            hour_trades = trades_df[trades_df['hour'] == hour]
            if len(hour_trades) > 0:
                print(f"  {hour:02d}:00 UTC: {len(hour_trades)} trades, {hour_trades['r'].mean():.3f}R avg")
        
        # By direction
        long_trades = trades_df[trades_df['direction'] == 'LONG']
        short_trades = trades_df[trades_df['direction'] == 'SHORT']
        
        print(f"\nBy direction:")
        if len(long_trades) > 0:
            print(f"  Long: {len(long_trades)} trades, {long_trades['r'].mean():.3f}R avg")
        if len(short_trades) > 0:
            print(f"  Short: {len(short_trades)} trades, {short_trades['r'].mean():.3f}R avg")
        
        return trades_df
    
    return None

if __name__ == "__main__":
    trades = run_data_driven_strategy()
