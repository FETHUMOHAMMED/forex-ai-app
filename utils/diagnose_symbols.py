import MetaTrader5 as mt5

mt5.initialize()
print("📋 All symbols available in MT5:")
symbols = mt5.symbols_get()
forex_symbols = [s.name for s in symbols if s.name[:3] in ['EUR', 'GBP', 'USD', 'AUD', 'CAD', 'JPY'] and len(s.name) <= 8]
for sym in sorted(forex_symbols):
    print(f"   {sym}")
mt5.shutdown()