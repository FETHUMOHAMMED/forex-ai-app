"""Generate realistic test data for research pipeline testing."""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

def generate_realistic_forex_data(symbol="EURUSD", days=365):
    """Generate realistic forex data for testing."""
    print(f"Generating realistic {symbol} data for {days} days...")
    
    # Parameters
    base_price = 1.1000 if symbol == "EURUSD" else 1.2500 if symbol == "GBPUSD" else 140.00
    volatility = 0.0005  # Daily volatility
    
    # Generate timestamps
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start_date, end_date, freq='5min')
    
    # Generate price movement with trends
    np.random.seed(42)
    n = len(dates)
    
    # Create regime shifts
    regimes = np.zeros(n)
    current_regime = 0
    for i in range(n):
        if np.random.random() < 0.001:  # 0.1% chance of regime change
            current_regime = np.random.choice([-1, 0, 1])
        regimes[i] = current_regime
    
    # Generate returns with regime-dependent drift
    drift = regimes * 0.00001  # Small drift per bar
    returns = np.random.normal(drift, volatility, n)
    
    # Generate prices
    close = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLC
    high = close * (1 + np.abs(np.random.normal(0, volatility/2, n)))
    low = close * (1 - np.abs(np.random.normal(0, volatility/2, n)))
    open_price = close * (1 + np.random.normal(0, volatility/4, n))
    
    # Ensure high >= max(open, close) and low <= min(open, close)
    high = np.maximum(high, np.maximum(open_price, close))
    low = np.minimum(low, np.minimum(open_price, close))
    
    # Generate volume
    volume = np.random.randint(10, 1000, n)
    volume = volume * (1 + np.abs(returns) * 100)  # Higher volume on big moves
    
    # Generate spread
    spread = np.random.uniform(0.5, 2.0, n) / 10000
    spread = spread * (1 + np.abs(returns) * 50)  # Wider spread on volatility
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'symbol': symbol,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume.astype(int),
        'spread': spread,
        'bid': close - spread/2,
        'ask': close + spread/2,
    })
    
    print(f"Generated {len(df)} bars")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Price range: {df['low'].min():.5f} to {df['high'].max():.5f}")
    
    return df

def generate_all_data():
    """Generate data for multiple symbols."""
    import pickle
    from pathlib import Path
    
    # Create data directory if it doesn't exist
    Path("data/research").mkdir(parents=True, exist_ok=True)
    
    all_data = {}
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    timeframes = {"H4": 240, "M15": 15, "M5": 5}
    
    for symbol in symbols:
        all_data[symbol] = {}
        for tf_name, tf_minutes in timeframes.items():
            print(f"\nGenerating {symbol} {tf_name}...")
            
            if tf_name == "H4":
                # Generate 4h data
                df = generate_realistic_forex_data(symbol, days=365)
                df = df.iloc[::48]  # Sample every 48th 5-min bar for H4
            elif tf_name == "M15":
                # Generate 15min data
                df = generate_realistic_forex_data(symbol, days=365)
                df = df.iloc[::3]  # Sample every 3rd 5-min bar for M15
            else:
                # Generate 5min data
                df = generate_realistic_forex_data(symbol, days=365)
            
            all_data[symbol][tf_name] = df
            print(f"  {len(df)} bars")
    
    # Save data
    data_path = Path("data/research/all_historical_data.pkl")
    with open(data_path, 'wb') as f:
        pickle.dump(all_data, f)
    
    print(f"\nAll data saved to {data_path}")
    print(f"Total symbols: {len(all_data)}")
    for symbol, tfs in all_data.items():
        for tf, df in tfs.items():
            print(f"  {symbol} {tf}: {len(df)} bars")

if __name__ == "__main__":
    generate_all_data()
