"""Analyze real MT5 data to understand market conditions."""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

def analyze_mt5_data():
    """Analyze real MT5 data."""
    # Load data
    data_path = Path('data/research/mt5_historical_data.pkl')
    if not data_path.exists():
        data_path = Path('data/research/all_historical_data.pkl')
    
    if not data_path.exists():
        print("No data found")
        return
    
    with open(data_path, 'rb') as f:
        all_data = pickle.load(f)
    
    print("="*60)
    print("  REAL MT5 DATA ANALYSIS")
    print("="*60)
    
    for symbol, timeframes in all_data.items():
        print(f"\n{symbol}:")
        
        for tf, df in timeframes.items():
            if len(df) < 2:
                continue
            
            print(f"\n  {tf} Timeframe:")
            print(f"    Bars: {len(df)}")
            print(f"    Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"    Price range: {df['low'].min():.5f} to {df['high'].max():.5f}")
            
            # Calculate basic statistics
            df['returns'] = df['close'].pct_change()
            df['range_pips'] = (df['high'] - df['low']) / 0.0001
            df['body_pips'] = abs(df['close'] - df['open']) / 0.0001
            
            print(f"    Avg range: {df['range_pips'].mean():.1f} pips")
            print(f"    Avg body: {df['body_pips'].mean():.1f} pips")
            print(f"    Volatility (std): {df['returns'].std()*100:.3f}%")
            
            # Check for trends
            if len(df) > 20:
                df['ema_20'] = df['close'].ewm(span=20, min_periods=20).mean()
                df['ema_50'] = df['close'].ewm(span=50, min_periods=50).mean()
                
                bullish = (df['ema_20'] > df['ema_50']).sum()
                bearish = (df['ema_20'] < df['ema_50']).sum()
                
                print(f"    Bullish periods: {bullish} ({bullish/len(df)*100:.1f}%)")
                print(f"    Bearish periods: {bearish} ({bearish/len(df)*100:.1f}%)")
            
            # Count potential setups
            if 'spread' in df.columns:
                avg_spread = df['spread'].mean()
                max_spread = df['spread'].max()
                print(f"    Avg spread: {avg_spread:.1f} points")
                print(f"    Max spread: {max_spread:.1f} points")
            
            # Session analysis
            if 'timestamp' in df.columns:
                df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
                london_session = df[(df['hour'] >= 7) & (df['hour'] <= 11)]
                ny_session = df[(df['hour'] >= 12) & (df['hour'] <= 16)]
                
                print(f"    London session bars: {len(london_session)} ({len(london_session)/len(df)*100:.1f}%)")
                print(f"    NY session bars: {len(ny_session)} ({len(ny_session)/len(df)*100:.1f}%)")
                
                if len(london_session) > 0:
                    london_vol = london_session['returns'].std()*100
                    print(f"    London volatility: {london_vol:.3f}%")
                
                if len(ny_session) > 0:
                    ny_vol = ny_session['returns'].std()*100
                    print(f"    NY volatility: {ny_vol:.3f}%")
    
    print(f"\n{'='*60}")
    print("  RECOMMENDATIONS FOR STRATEGY")
    print(f"{'='*60}")
    print("""
Based on the real data analysis, consider:
1. What is the average daily range? (affects SL/TP settings)
2. What is the typical spread? (affects entry costs)
3. Which sessions have the most volatility? (best trading times)
4. Is there a clear trend or is it ranging? (determines strategy type)
5. How many bars do you have? (affects statistical significance)
""")

if __name__ == "__main__":
    analyze_mt5_data()
