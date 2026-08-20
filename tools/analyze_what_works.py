"""Analyze what actually works in the USDJPY data."""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

def analyze_what_works():
    """Comprehensive analysis of USDJPY price action."""
    print("="*60)
    print("  COMPREHENSIVE USDJPYm ANALYSIS")
    print("="*60)
    
    # Load data
    with open('data/research/mt5_historical_data.pkl', 'rb') as f:
        all_data = pickle.load(f)
    
    data = all_data['USDJPYm']['M15'].copy()  # Use M15 for less noise
    
    print(f"\nData: {len(data)} M15 bars")
    print(f"Period: {data['timestamp'].min()} to {data['timestamp'].max()}")
    
    # Calculate returns over different horizons
    print("\n1. RETURN ANALYSIS")
    for horizon in [1, 5, 10, 20, 50, 100]:
        returns = data['close'].pct_change(horizon).dropna()
        win_rate = (returns > 0).mean() * 100
        avg_win = returns[returns > 0].mean() * 100
        avg_loss = returns[returns < 0].mean() * 100
        print(f"  {horizon}-bar returns:")
        print(f"    Win rate: {win_rate:.1f}%")
        print(f"    Avg win: {avg_win:.3f}%")
        print(f"    Avg loss: {avg_loss:.3f}%")
        print(f"    Net: {returns.mean()*100:.3f}%")
    
    # Analyze by time of day
    print("\n2. TIME OF DAY ANALYSIS")
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    data['returns'] = data['close'].pct_change()
    
    for hour in range(24):
        hour_data = data[data['hour'] == hour]
        if len(hour_data) > 30:
            avg_ret = hour_data['returns'].mean() * 10000  # in pips
            win_rate = (hour_data['returns'] > 0).mean() * 100
            print(f"  {hour:02d}:00 UTC - {len(hour_data)} bars, avg {avg_ret:.2f} pips, {win_rate:.0f}% win")
    
    # Analyze by day of week
    print("\n3. DAY OF WEEK ANALYSIS")
    data['day'] = pd.to_datetime(data['timestamp']).dt.day_name()
    
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        day_data = data[data['day'] == day]
        if len(day_data) > 100:
            avg_ret = day_data['returns'].mean() * 10000
            win_rate = (day_data['returns'] > 0).mean() * 100
            print(f"  {day}: {len(day_data)} bars, avg {avg_ret:.2f} pips, {win_rate:.0f}% win")
    
    # Analyze trend characteristics
    print("\n4. TREND CHARACTERISTICS")
    
    # Calculate EMAs
    data['ema_50'] = data['close'].ewm(span=50, min_periods=50).mean()
    data['ema_200'] = data['close'].ewm(span=200, min_periods=200).mean()
    
    # Measure trend persistence
    data['above_ema'] = data['close'] > data['ema_50']
    data['trend_change'] = data['above_ema'] != data['above_ema'].shift()
    trend_changes = data['trend_change'].sum()
    avg_trend_duration = len(data) / trend_changes if trend_changes > 0 else 0
    
    print(f"  Trend changes: {trend_changes}")
    print(f"  Average trend duration: {avg_trend_duration:.0f} bars")
    
    # Measure pullback depth
    data['pullback'] = 0.0
    for i in range(50, len(data)):
        if data['close'].iloc[i] > data['ema_50'].iloc[i]:
            # In uptrend
            recent_high = data['high'].iloc[i-20:i].max()
            data.loc[data.index[i], 'pullback'] = (data['close'].iloc[i] - recent_high) / recent_high
        else:
            # In downtrend
            recent_low = data['low'].iloc[i-20:i].min()
            data.loc[data.index[i], 'pullback'] = (data['close'].iloc[i] - recent_low) / recent_low
    
    # Analyze pullback characteristics
    pullbacks = data[data['pullback'] < 0]['pullback']
    if len(pullbacks) > 0:
        print(f"\n  Pullback analysis:")
        print(f"    Median pullback: {pullbacks.median()*100:.2f}%")
        print(f"    25th percentile: {pullbacks.quantile(0.25)*100:.2f}%")
        print(f"    75th percentile: {pullbacks.quantile(0.75)*100:.2f}%")
    
    # Test different R:R ratios
    print("\n5. OPTIMAL R:R RATIO TEST")
    
    # Simple momentum strategy
    data['momentum'] = data['close'].pct_change(10)
    
    for rr_ratio in [1.0, 1.5, 2.0, 2.5, 3.0]:
        wins = 0
        losses = 0
        
        for i in range(50, len(data)):
            if data['momentum'].iloc[i] > 0:
                # Long signal
                entry = data['close'].iloc[i]
                sl = entry * 0.998  # 0.2% stop
                tp = entry * (1 + 0.002 * rr_ratio)  # RR * stop distance
                
                for j in range(i+1, min(i+100, len(data))):
                    if data['low'].iloc[j] <= sl:
                        losses += 1
                        break
                    elif data['high'].iloc[j] >= tp:
                        wins += 1
                        break
        
        total = wins + losses
        if total > 0:
            win_rate = wins / total * 100
            expectancy = (win_rate / 100 * rr_ratio) - ((100 - win_rate) / 100)
            print(f"  R:R {rr_ratio:.1f}: {total} trades, {win_rate:.0f}% win, expectancy {expectancy:.3f}R")
    
    print("\n" + "="*60)
    print("  KEY INSIGHTS")
    print("="*60)
    
    # Summarize findings
    print("""
Based on this analysis, we can determine:
1. Which timeframes have the most predictable moves
2. Which sessions are best for trading
3. Which days offer the best opportunities
4. What R:R ratio is most suitable
5. How deep pullbacks typically go
""")

if __name__ == "__main__":
    analyze_what_works()
