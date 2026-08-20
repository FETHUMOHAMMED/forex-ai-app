"""Download maximum available historical data from MT5."""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import pickle
from pathlib import Path

def download_full_history():
    """Download as much historical data as possible."""
    print("Downloading maximum historical data...")
    
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return None
    
    # Available micro symbols
    symbols = ["EURUSDm", "GBPUSDm", "USDJPYm", "AUDUSDm"]
    timeframes = {
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4
    }
    
    all_data = {}
    current_time = datetime.now()
    
    # Try different history lengths
    history_periods = [
        ("1 day", 1),
        ("1 week", 7),
        ("1 month", 30),
        ("3 months", 90),
        ("6 months", 180),
        ("1 year", 365),
        ("2 years", 730),
        ("5 years", 1825)
    ]
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"Downloading {symbol}")
        print(f"{'='*60}")
        
        # Test what history is available
        for period_name, days in history_periods:
            start = current_time - timedelta(days=days)
            rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start, current_time)
            
            if rates is not None and len(rates) > 0:
                print(f"  {period_name}: {len(rates)} bars available")
            else:
                print(f"  {period_name}: No data")
                break
        
        # Download M5 data (most granular)
        print(f"\n  Downloading M5 data...")
        
        # Try 1 year first
        start = current_time - timedelta(days=365)
        rates_m5 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start, current_time)
        
        if rates_m5 is None or len(rates_m5) == 0:
            # Try 6 months
            start = current_time - timedelta(days=180)
            rates_m5 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start, current_time)
            print(f"  Using 6 months: {len(rates_m5) if rates_m5 is not None else 0} bars")
        
        if rates_m5 is not None and len(rates_m5) > 0:
            df_m5 = pd.DataFrame(rates_m5)
            df_m5['timestamp'] = pd.to_datetime(df_m5['time'], unit='s')
            df_m5['symbol'] = symbol
            
            # Store data
            if symbol not in all_data:
                all_data[symbol] = {}
            all_data[symbol]['M5'] = df_m5
            
            print(f"  M5: {len(df_m5)} bars from {df_m5['timestamp'].min()} to {df_m5['timestamp'].max()}")
            
            # Download M15
            print(f"  Downloading M15 data...")
            rates_m15 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start, current_time)
            if rates_m15 is not None and len(rates_m15) > 0:
                df_m15 = pd.DataFrame(rates_m15)
                df_m15['timestamp'] = pd.to_datetime(df_m15['time'], unit='s')
                all_data[symbol]['M15'] = df_m15
                print(f"  M15: {len(df_m15)} bars")
            
            # Download H1
            print(f"  Downloading H1 data...")
            rates_h1 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start, current_time)
            if rates_h1 is not None and len(rates_h1) > 0:
                df_h1 = pd.DataFrame(rates_h1)
                df_h1['timestamp'] = pd.to_datetime(df_h1['time'], unit='s')
                all_data[symbol]['H1'] = df_h1
                print(f"  H1: {len(df_h1)} bars")
            
            # Download H4
            print(f"  Downloading H4 data...")
            rates_h4 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H4, start, current_time)
            if rates_h4 is not None and len(rates_h4) > 0:
                df_h4 = pd.DataFrame(rates_h4)
                df_h4['timestamp'] = pd.to_datetime(df_h4['time'], unit='s')
                all_data[symbol]['H4'] = df_h4
                print(f"  H4: {len(df_h4)} bars")
    
    mt5.shutdown()
    
    # Save data
    if all_data:
        Path('data/research').mkdir(parents=True, exist_ok=True)
        with open('data/research/mt5_historical_data.pkl', 'wb') as f:
            pickle.dump(all_data, f)
        
        print(f"\n{'='*60}")
        print("DATA DOWNLOAD COMPLETE")
        print(f"{'='*60}")
        for symbol, timeframes in all_data.items():
            print(f"\n{symbol}:")
            for tf, df in timeframes.items():
                print(f"  {tf}: {len(df)} bars from {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return all_data
    
    return None

if __name__ == "__main__":
    data = download_full_history()
    
    if data:
        print("\n? SUCCESS: Historical data downloaded")
    else:
        print("\n? FAILED: Could not download historical data")
