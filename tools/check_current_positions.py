import MetaTrader5 as mt5
mt5.initialize()
positions = mt5.positions_get()
if positions:
    print(f"Open positions: {len(positions)}")
    for p in positions:
        print(f"\n  {p.symbol} {'SELL' if p.type == 1 else 'BUY'} @ {p.price_open}")
        print(f"  Ticket: {p.ticket}")
        print(f"  SL: {p.sl}")
        print(f"  TP: {p.tp}")
        print(f"  Profit: ${p.profit:.2f}")
        if p.sl == 0 and p.tp == 0:
            print(f"  [UNPROTECTED] No SL/TP")
else:
    print("No open positions")
mt5.shutdown()
