"""Close unprotected position 589629837 - currently +$3.75 in profit"""
import MetaTrader5 as mt5

mt5.initialize()
position = mt5.positions_get(ticket=589629837)

if position:
    p = position[0]
    
    # Close at market
    tick = mt5.symbol_info_tick(p.symbol)
    if tick is None:
        print("Cannot get tick")
        mt5.shutdown()
        exit()
    
    close_price = tick.bid if p.type == 0 else tick.ask
    close_type = mt5.ORDER_TYPE_SELL if p.type == 0 else mt5.ORDER_TYPE_BUY
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": p.ticket,
        "symbol": p.symbol,
        "volume": p.volume,
        "type": close_type,
        "price": close_price,
        "deviation": 30,
        "comment": "Close unprotected position - exchange mode no SL/TP support",
    }
    
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"POSITION CLOSED")
        print(f"  Ticket: {p.ticket}")
        print(f"  Profit: ${result.profit if hasattr(result, 'profit') else p.profit:.2f}")
        print(f"  Reason: No SL/TP protection possible on EURUSDm (exchange mode)")
    else:
        print(f"Close failed: retcode={result.retcode if result else 'None'}")
        print(f"  Comment: {result.comment if result else 'N/A'}")
else:
    print("Position not found - already closed or invalid ticket")

mt5.shutdown()
