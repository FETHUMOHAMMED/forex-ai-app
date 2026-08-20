import MetaTrader5 as mt5
mt5.initialize()
info = mt5.account_info()
if info:
    print(f"Balance: ${info.balance:.2f}")
    print(f"Equity: ${info.equity:.2f}")
    print(f"Profit: ${info.profit:.2f}")
    print(f"Unrealized: ${info.equity - info.balance:.2f}")
    print(f"Account: {info.login}")
    print(f"Server: {info.server}")

positions = mt5.positions_get()
if positions:
    for p in positions:
        print(f"\nPosition: {p.symbol}")
        print(f"  Ticket: {p.ticket}")
        print(f"  Volume: {p.volume}")
        print(f"  Open Price: {p.price_open}")
        print(f"  Current Price: {p.price_current}")
        print(f"  Profit: ${p.profit:.2f}")
else:
    print("No open positions")
mt5.shutdown()
