"""Add symbols to MT5 Market Watch."""
import MetaTrader5 as mt5
import time

def add_symbols_to_market_watch():
    """Add all required symbols to MT5 Market Watch."""
    print("Adding symbols to MT5 Market Watch...")
    
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return False
    
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD"]
    
    for symbol in symbols:
        print(f"\nProcessing {symbol}...")
        
        # Try to select the symbol
        if mt5.symbol_select(symbol, True):
            print(f"  Added {symbol} to Market Watch")
            
            # Wait a moment for symbol to load
            time.sleep(1)
            
            # Check if symbol is now available
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is not None:
                print(f"  Symbol info: {symbol_info.name}")
                print(f"  Bid: {symbol_info.bid}")
                print(f"  Ask: {symbol_info.ask}")
                print(f"  Spread: {symbol_info.spread}")
            else:
                print(f"  Symbol info not available yet: {mt5.last_error()}")
        else:
            print(f"  FAILED to add {symbol}: {mt5.last_error()}")
    
    # Get all visible symbols
    print("\nVisible symbols in Market Watch:")
    visible_symbols = mt5.symbols_get(group="*")
    if visible_symbols:
        for sym in visible_symbols[:20]:  # Show first 20
            print(f"  {sym.name}")
    
    mt5.shutdown()
    return True

if __name__ == "__main__":
    add_symbols_to_market_watch()
