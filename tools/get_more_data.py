"""Try to get more historical data from MT5."""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import pickle
from pathlib import Path

def get_maximum_history():
    """Try multiple methods to get maximum historical data."""
    print("Attempting to get maximum historical data...")
    
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return None
    
    symbol = "USDJPYm"
    current_time = datetime.now()
    
    # Method 1: Try copy_rates_from_pos (may give more history)
    print(f"\nMethod 1: copy_rates_from_pos for {symbol}")
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 10000)
    if rates is not None and len(rates) > 0:
        print(f"  Got {len(rates)} bars")
        print(f"  Date range: {datetime.fromtimestamp(rates[0]['time'])} to {datetime.fromtimestamp(rates[-1]['time'])}")
    else:
        print(f"  Failed: {mt5.last_error()}")
    
    # Method 2: Try different date ranges
    print(f"\nMethod 2: Testing different date ranges")
    ranges = [
        ("Last 1 year", current_time - timedelta(days=365)),
        ("Last 2 years", current_time - timedelta(days=730)),
        ("Last 3 years", current_time - timedelta(days=1095)),
        ("Last 5 years", current_time - timedelta(days=1825)),
    ]
    
    for name, start_date in ranges:
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H4, start_date, current_time)
        if rates is not None and len(rates) > 0:
            print(f"  {name}: {len(rates)} bars")
        else:
            print(f"  {name}: No data - {mt5.last_error()}")
    
    # Method 3: Try different symbols
    print(f"\nMethod 3: Testing other symbols")
    symbols_to_test = ["USDJPY", "USDJPYm", "USDJPY#", "USDJPYmicro"]
    
    for sym in symbols_to_test:
        info = mt5.symbol_info(sym)
        if info is not None:
            print(f"  {sym}: Available")
            rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H4, 0, 10000)
            if rates is not None and len(rates) > 0:
                print(f"    Got {len(rates)} bars")
                print(f"    Range: {datetime.fromtimestamp(rates[0]['time'])} to {datetime.fromtimestamp(rates[-1]['time'])}")
        else:
            print(f"  {sym}: Not available")
    
    # Method 4: Try to enable more history in symbol
    print(f"\nMethod 4: Checking symbol settings")
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is not None:
        print(f"  Symbol: {symbol_info.name}")
        print(f"  Trade mode: {symbol_info.trade_mode}")
        print(f"  Digits: {symbol_info.digits}")
        print(f"  Spread: {symbol_info.spread}")
        print(f"  Point: {symbol_info.point}")
        
        # Check if we can modify symbol settings
        if mt5.symbol_select(symbol, True):
            print(f"  Symbol selected for Market Watch")
    
    mt5.shutdown()
    return None

if __name__ == "__main__":
    get_maximum_history()
