"""Test MT5 connection and data availability."""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd

def test_mt5_connection():
    """Test if MT5 is running and accessible."""
    print("Testing MT5 connection...")
    
    # Try to initialize MT5
    if not mt5.initialize():
        print(f"FAILED: MT5 initialization error: {mt5.last_error()}")
        print("\nPossible issues:")
        print("1. MT5 terminal is not running")
        print("2. MT5 terminal is running but not logged in")
        print("3. Python can't connect to MT5 terminal")
        return False
    
    print("SUCCESS: MT5 initialized")
    
    # Get account info
    account_info = mt5.account_info()
    if account_info is None:
        print("FAILED: No account info available")
        print("Make sure you are logged into your MT5 account")
        mt5.shutdown()
        return False
    
    print(f"Account: {account_info.login}")
    print(f"Server: {account_info.server}")
    print(f"Balance: ${account_info.balance:.2f}")
    print(f"Equity: ${account_info.equity:.2f}")
    
    # Test symbol access
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    print("\nTesting symbol access:")
    for symbol in symbols:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is not None:
            print(f"  {symbol}: Available")
        else:
            print(f"  {symbol}: NOT AVAILABLE")
    
    # Test data retrieval
    print("\nTesting data retrieval (last 1 hour):")
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=1)
    
    rates = mt5.copy_rates_range("EURUSD", mt5.TIMEFRAME_M5, start_date, end_date)
    if rates is not None and len(rates) > 0:
        print(f"  EURUSD M5: {len(rates)} bars retrieved")
        df = pd.DataFrame(rates)
        print(f"  Date range: {pd.to_datetime(df['time'], unit='s').min()} to {pd.to_datetime(df['time'], unit='s').max()}")
    else:
        print(f"  EURUSD M5: NO DATA - Error: {mt5.last_error()}")
    
    mt5.shutdown()
    return True

if __name__ == "__main__":
    test_mt5_connection()
