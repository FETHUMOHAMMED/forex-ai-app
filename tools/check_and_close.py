import MetaTrader5 as mt5
mt5.initialize()

# Check position
positions = mt5.positions_get(ticket=591202079)
if positions:
    p = positions[0]
    print(f"Position found: {p.symbol} profit=${p.profit}")
    print(f"Type: {p.type} (0=BUY, 1=SELL)")
    
    # Close SELL with BUY
    close_type = mt5.ORDER_TYPE_BUY if p.type == 1 else mt5.ORDER_TYPE_SELL
    
    tick = mt5.symbol_info_tick(p.symbol)
    print(f"Bid: {tick.bid} Ask: {tick.ask}")
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": p.ticket,
        "symbol": p.symbol,
        "volume": p.volume,
        "type": close_type,
        "price": tick.ask if p.type == 1 else tick.bid,
        "deviation": 100,
        "magic": 234000,
        "comment": "close_unprotected",
    }
    
    result = mt5.order_send(request)
    print(f"Result: {result}")
    if result:
        print(f"Retcode: {result.retcode}")
        print(f"Comment: {result.comment}")
else:
    print("Position 591202079 not found - may already be closed or different ticket")

mt5.shutdown()
