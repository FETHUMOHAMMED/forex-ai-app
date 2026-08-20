import MetaTrader5 as mt5
mt5.initialize()

# Check Live_Micro account
info = mt5.account_info()
print(f"Account: {info.login}")
print(f"Balance: ${info.balance:.2f}")
print(f"Equity: ${info.equity:.2f}")

# Check all open positions
positions = mt5.positions_get()
if positions:
    print(f"\nOpen positions: {len(positions)}")
    for p in positions:
        direction = "SELL" if p.type == 1 else "BUY"
        print(f"\n  {p.symbol} {direction}")
        print(f"  Ticket: {p.ticket}")
        print(f"  Volume: {p.volume}")
        print(f"  Entry: {p.price_open}")
        print(f"  Current: {p.price_current}")
        print(f"  SL: {p.sl}")
        print(f"  TP: {p.tp}")
        print(f"  Profit: ${p.profit:.2f}")
        if p.sl == 0 and p.tp == 0:
            print(f"  [UNPROTECTED] No SL/TP!")
        else:
            print(f"  [PROTECTED] SL/TP set")
else:
    print("No open positions")

mt5.shutdown()
