"""Download data using available micro symbols."""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import pickle
from pathlib import Path

def download_micro_data():
    """Download data for available micro symbols."""
    print("Checking available symbols...")
    
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return
    
    # Check for micro symbols
    test_symbols = ["EURUSDm", "GBPUSDm", "USDJPYm", "AUDUSDm"]
    available = []
    
    for symbol in test_symbols:
        info = mt5.symbol_info(symbol)
        if info is not None:
            available.append(symbol)
            print(f"  {symbol}: Available")
        else:
            print(f"  {symbol}: Not available")
    
    if not available:
        print("\nNo micro symbols found. Using visible symbols:")
        visible = mt5.symbols_get(group="*")
        for sym in visible[:10]:
            if "USD" in sym.name or "EUR" in sym.name:
                print(f"  {sym.name}")
    
    # Download data for available symbols
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    all_data = {}
    
    for symbol in available[:3]:  # Use first 3 available
        print(f"\nDownloading {symbol} M5 data...")
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start_date, end_date)
        
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df['symbol'] = symbol
            
            # Store as M5 timeframe
            if symbol not in all_data:
                all_data[symbol] = {}
            all_data[symbol]["M5"] = df
            
            print(f"  Downloaded {len(df)} bars")
        else:
            print(f"  No data available: {mt5.last_error()}")
    
    mt5.shutdown()
    
    # Save data
    if all_data:
        Path("data/research").mkdir(parents=True, exist_ok=True)
        with open("data/research/all_historical_data.pkl", "wb") as f:
            pickle.dump(all_data, f)
        print(f"\nSaved data for {len(all_data)} symbols")
    else:
        print("\nNo data downloaded")
    
    return all_data

if __name__ == "__main__":
    download_micro_data()
