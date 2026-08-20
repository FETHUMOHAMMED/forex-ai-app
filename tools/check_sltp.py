import MetaTrader5 as mt5
mt5.initialize()
positions = mt5.positions_get(ticket=591202079)
if positions:
    p = positions[0]
    print(f"Position: {p.symbol} {'SELL' if p.type == 1 else 'BUY'}")
    print(f"Entry: {p.price_open}")
    print(f"Current: {p.price_current}")
    print(f"SL: {p.sl}")
    print(f"TP: {p.tp}")
    print(f"Volume: {p.volume}")
    print(f"Profit: ${p.profit}")
    
    if p.sl == 0 and p.tp == 0:
        print("\n[WARNING] NO SL/TP - position is UNPROTECTED!")
        print("Exchange mode EURUSDm rejects SL/TP on market orders")
    else:
        print("\nSL/TP: PROTECTED")
mt5.shutdown()
