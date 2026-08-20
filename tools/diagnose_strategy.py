"""Diagnose why strategy generates no trades."""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

def diagnose_strategy():
    """Analyze why strategy generates 0 trades."""
    print("Diagnosing strategy...")
    
    # Load data
    with open("data/research/all_historical_data.pkl", "rb") as f:
        all_data = pickle.load(f)
    
    # Get EURUSD M5 data
    data = all_data["EURUSD"]["M5"]
    
    print(f"\nData shape: {data.shape}")
    print(f"Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
    
    # Check EMA conditions
    print("\n1. Checking EMA conditions...")
    data['ema_50'] = data['close'].ewm(span=50, min_periods=50).mean()
    data['ema_200'] = data['close'].ewm(span=200, min_periods=200).mean()
    
    bullish = (data['ema_50'] > data['ema_200']).sum()
    bearish = (data['ema_50'] < data['ema_200']).sum()
    print(f"  Bullish bars: {bullish} ({bullish/len(data)*100:.1f}%)")
    print(f"  Bearish bars: {bearish} ({bearish/len(data)*100:.1f}%)")
    
    # Check liquidity sweep conditions
    print("\n2. Checking liquidity sweep conditions...")
    sweep_count = 0
    for i in range(50, len(data)):
        lookback = data.iloc[i-50:i]
        if data['ema_50'].iloc[i] > data['ema_200'].iloc[i]:  # Bullish
            recent_low = lookback['low'].min()
            if data['low'].iloc[i] < recent_low:
                sweep_count += 1
        elif data['ema_50'].iloc[i] < data['ema_200'].iloc[i]:  # Bearish
            recent_high = lookback['high'].max()
            if data['high'].iloc[i] > recent_high:
                sweep_count += 1
    
    print(f"  Liquidity sweeps detected: {sweep_count}")
    
    # Check FVG conditions
    print("\n3. Checking FVG conditions...")
    fvg_count = 0
    for i in range(2, len(data)):
        # Bullish FVG
        if data['high'].iloc[i-2] < data['low'].iloc[i]:
            gap_size = (data['low'].iloc[i] - data['high'].iloc[i-2]) / 0.0001
            if gap_size >= 3.0:
                fvg_count += 1
    
    print(f"  Valid FVGs detected: {fvg_count}")
    
    # Check combined conditions
    print("\n4. Checking combined conditions...")
    combined_count = 0
    for i in range(200, len(data)):
        # All conditions must be met
        if data['ema_50'].iloc[i] > data['ema_200'].iloc[i]:  # Bullish
            lookback = data.iloc[i-50:i]
            recent_low = lookback['low'].min()
            if data['low'].iloc[i] < recent_low:  # Sweep
                if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:  # FVG
                    combined_count += 1
    
    print(f"  Trades that would trigger: {combined_count}")
    
    # Check if spread filter is too strict
    print("\n5. Checking spread filter...")
    if 'spread' in data.columns:
        high_spread = (data['spread'] > 1.5).sum()
        print(f"  Bars with spread > 1.5 pips: {high_spread} ({high_spread/len(data)*100:.1f}%)")
        print(f"  Average spread: {data['spread'].mean():.2f} pips")
    
    # Check session filter
    print("\n6. Checking session filter...")
    data['hour'] = data['timestamp'].dt.hour
    session_bars = ((data['hour'] >= 7) & (data['hour'] <= 11)).sum()
    print(f"  Bars in session (7-11 UTC): {session_bars} ({session_bars/len(data)*100:.1f}%)")
    
    print("\nRECOMMENDATIONS:")
    print("1. Relax sweep_wick_ratio from 0.5 to 0.3")
    print("2. Reduce FVG min size from 3.0 to 1.5 pips")
    print("3. Extend session hours from 7-11 to 6-14")
    print("4. Increase lookback from 50 to 100 bars")

if __name__ == "__main__":
    diagnose_strategy()
