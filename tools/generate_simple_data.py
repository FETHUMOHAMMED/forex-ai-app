"""Generate simple test data that actually saves properly."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
from pathlib import Path

def generate_simple_data():
    """Generate simple but valid test data."""
    print("Generating simple test data...")
    
    # Create timestamps
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    dates = pd.date_range(start_date, end_date, freq='5min')
    
    n = len(dates)
    print(f"Generating {n} bars...")
    
    # Generate OHLC data
    np.random.seed(42)
    base_price = 1.1000
    
    # Generate returns with some structure
    returns = np.random.normal(0, 0.0002, n)
    # Add some trend
    trend = np.linspace(0, 0.05, n)  # 5% drift over year
    close = base_price * np.exp(np.cumsum(returns) + trend)
    
    # Generate OHLC from close
    high = close * (1 + np.abs(np.random.normal(0, 0.0005, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.0005, n)))
    open_price = close * (1 + np.random.normal(0, 0.0003, n))
    
    # Ensure high >= open, close and low <= open, close
    high = np.maximum(high, np.maximum(open_price, close))
    low = np.minimum(low, np.minimum(open_price, close))
    
    # Volume
    volume = np.random.randint(100, 1000, n)
    
    # Spread in pips (0.0001 = 1 pip)
    spread = np.random.uniform(0.5, 2.0, n) * 0.0001
    
    # Create DataFrame
    data = pd.DataFrame({
        'timestamp': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'spread': spread,
    })
    
    # Create nested structure: {symbol: {timeframe: dataframe}}
    all_data = {
        'EURUSD': {
            'M5': data.copy()
        },
        'GBPUSD': {
            'M5': data.copy()  # Same pattern, different price would be better
        },
        'USDJPY': {
            'M5': data.copy()
        }
    }
    
    # Save to pickle
    output_path = Path('data/research/all_historical_data.pkl')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'wb') as f:
        pickle.dump(all_data, f)
    
    print(f"Data saved to {output_path}")
    print(f"EURUSD M5: {len(data)} bars")
    print(f"Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
    print(f"Price range: {data['low'].min():.5f} to {data['high'].max():.5f}")
    
    return all_data

if __name__ == "__main__":
    all_data = generate_simple_data()
    
    # Verify the data can be loaded
    print("\nVerifying data...")
    with open('data/research/all_historical_data.pkl', 'rb') as f:
        loaded = pickle.load(f)
    
    print(f"Loaded keys: {list(loaded.keys())}")
    print(f"EURUSD keys: {list(loaded['EURUSD'].keys())}")
    print(f"M5 shape: {loaded['EURUSD']['M5'].shape}")
    print("SUCCESS: Data structure is correct")
