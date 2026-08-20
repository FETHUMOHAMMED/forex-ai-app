"""Download historical data from MT5 for research."""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import json

def download_mt5_data(symbol: str, timeframe, start_date: datetime, end_date: datetime):
    """Download historical data from MT5."""
    if not mt5.initialize():
        print("MT5 initialization failed")
        return None
    
    # Convert timeframe
    tf_map = {
        "H4": mt5.TIMEFRAME_H4,
        "M15": mt5.TIMEFRAME_M15,
        "M5": mt5.TIMEFRAME_M5,
        "M1": mt5.TIMEFRAME_M1
    }
    
    tf = tf_map.get(timeframe)
    if tf is None:
        print(f"Invalid timeframe: {timeframe}")
        return None
    
    # Download rates
    rates = mt5.copy_rates_range(symbol, tf, start_date, end_date)
    
    if rates is None or len(rates) == 0:
        print(f"No data downloaded for {symbol} {timeframe}")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(rates)
    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
    df['symbol'] = symbol
    df['timeframe'] = timeframe
    
    # Calculate spread if not available
    if 'spread' not in df.columns:
        # Get tick data for spread
        ticks = mt5.copy_ticks_range(symbol, start_date, end_date, mt5.COPY_TICKS_ALL)
        if ticks is not None and len(ticks) > 0:
            tick_df = pd.DataFrame(ticks)
            tick_df['timestamp'] = pd.to_datetime(tick_df['time'], unit='s')
            tick_df['spread'] = (tick_df['ask'] - tick_df['bid']) / 0.0001
            
            # Resample to bar timeframe
            spread_resampled = tick_df.set_index('timestamp')['spread'].resample(
                '5min' if timeframe == "M5" else '15min' if timeframe == "M15" else '4h'
            ).mean()
            
            df['spread'] = spread_resampled.values[:len(df)]
    
    mt5.shutdown()
    return df

def download_all_data():
    """Download all required data for research."""
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    timeframes = ["H4", "M15", "M5"]
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # 1 year of history
    
    all_data = {}
    
    for symbol in symbols:
        all_data[symbol] = {}
        for tf in timeframes:
            print(f"Downloading {symbol} {tf}...")
            df = download_mt5_data(symbol, tf, start_date, end_date)
            if df is not None:
                all_data[symbol][tf] = df
                print(f"  Downloaded {len(df)} bars")
            else:
                print(f"  Failed to download {symbol} {tf}")
    
    # Save all data
    import pickle
    with open('data/research/all_historical_data.pkl', 'wb') as f:
        pickle.dump(all_data, f)
    
    print("\nData download complete!")
    print(f"Symbols: {list(all_data.keys())}")
    for symbol, tfs in all_data.items():
        for tf, df in tfs.items():
            print(f"  {symbol} {tf}: {len(df)} bars")

if __name__ == "__main__":
    download_all_data()
