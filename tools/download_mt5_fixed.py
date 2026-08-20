"""Download MT5 data with fixed parameters."""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import pickle
from pathlib import Path

def download_mt5_data_fixed():
    """Download MT5 data with correct parameters."""
    print("Testing MT5 data download...")
    
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return None
    
    # Check available symbols
    symbols_to_try = ["EURUSDm", "GBPUSDm", "USDJPYm", "EURUSD", "GBPUSD", "USDJPY"]
    
    for symbol in symbols_to_try:
        print(f"\nTesting {symbol}...")
        
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"  Symbol not found: {mt5.last_error()}")
            continue
        
        print(f"  Symbol found: {symbol_info.name}")
        print(f"  Trade mode: {symbol_info.trade_mode}")
        
        # Try different date ranges
        current_time = datetime.now()
        
        # Try last 24 hours first
        print("  Trying last 24 hours...")
        start = current_time - timedelta(hours=24)
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start, current_time)
        
        if rates is not None and len(rates) > 0:
            print(f"  SUCCESS: Got {len(rates)} bars")
            df = pd.DataFrame(rates)
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            
            # Create data structure
            all_data = {
                symbol: {
                    'M5': df
                }
            }
            
            # Save data
            Path('data/research').mkdir(parents=True, exist_ok=True)
            with open('data/research/all_historical_data.pkl', 'wb') as f:
                pickle.dump(all_data, f)
            
            print(f"\nSaved {len(df)} bars to data/research/all_historical_data.pkl")
            print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            mt5.shutdown()
            return all_data
        else:
            error = mt5.last_error()
            print(f"  Failed: {error}")
            
            # Try last hour
            print("  Trying last hour...")
            start = current_time - timedelta(hours=1)
            rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, current_time)
            
            if rates is not None and len(rates) > 0:
                print(f"  Got {len(rates)} M1 bars")
                df = pd.DataFrame(rates)
                df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                
                all_data = {
                    symbol: {
                        'M1': df
                    }
                }
                
                Path('data/research').mkdir(parents=True, exist_ok=True)
                with open('data/research/all_historical_data.pkl', 'wb') as f:
                    pickle.dump(all_data, f)
                
                print(f"\nSaved {len(df)} bars")
                
                mt5.shutdown()
                return all_data
            else:
                print(f"  Failed: {mt5.last_error()}")
    
    mt5.shutdown()
    print("\nCould not download data from MT5")
    return None

if __name__ == "__main__":
    data = download_mt5_data_fixed()
    
    if data:
        print("\nData download successful!")
        for symbol, timeframes in data.items():
            for tf, df in timeframes.items():
                print(f"  {symbol} {tf}: {len(df)} bars")
    else:
        print("\nData download failed")
        print("Using synthetic data instead...")
        from generate_simple_data import generate_simple_data
        generate_simple_data()
