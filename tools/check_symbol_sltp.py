"""Check which symbols support SL/TP"""
import MetaTrader5 as mt5

mt5.initialize()

symbols_to_check = ['EURUSD', 'EURUSDm', 'EURUSD.', 'EURUSDpro', 'GBPUSD', 'GBPUSDm']
print("=" * 60)
print("  SYMBOL SL/TP SUPPORT CHECK")
print("=" * 60)

for sym in symbols_to_check:
    mt5.symbol_select(sym, True)
    info = mt5.symbol_info(sym)
    if info:
        mode = info.trade_mode
        mode_name = {0: 'FULL (SL/TP OK)', 1: 'LIMIT', 2: 'STOP', 3: 'LIMIT_STOP', 4: 'EXCHANGE (NO SL/TP)'}.get(mode, f'UNKNOWN({mode})')
        stops = info.trade_stops_level
        print(f"\n  {sym}:")
        print(f"    Trade Mode: {mode_name}")
        print(f"    Stops Level: {stops} points")
        print(f"    Volume Min: {info.volume_min}")
        print(f"    Supports SL/TP: {'YES' if mode == 0 else 'NO'}")
    else:
        print(f"\n  {sym}: NOT AVAILABLE")

mt5.shutdown()
