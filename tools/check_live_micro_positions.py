import MetaTrader5 as mt5
mt5.initialize()
mt5.login(REDACTED_LIVE_ACCOUNT, password="Fetherames1", server="Exness-MT5Real10")
info = mt5.account_info()
print(f"Account: {info.login}")
print(f"Balance: ${info.balance:.2f}")
print(f"Equity: ${info.equity:.2f}")
positions = mt5.positions_get()
if positions:
    for p in positions:
        direction = "SELL" if p.type == 1 else "BUY"
        print(f"\nPosition: {p.symbol} {direction}")
        print(f"  Ticket: {p.ticket}")
        print(f"  Volume: {p.volume}")
        print(f"  Entry: {p.price_open}")
        print(f"  SL: {p.sl}")
        print(f"  TP: {p.tp}")
        print(f"  Profit: ${p.profit:.2f}")
else:
    print("No positions on Live_Micro")
mt5.shutdown()
