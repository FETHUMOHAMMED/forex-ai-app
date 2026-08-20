import MetaTrader5 as mt5
mt5.initialize()
positions = mt5.positions_get(ticket=591202079)
if positions:
    p = positions[0]
    tick = mt5.symbol_info_tick(p.symbol)
    result = mt5.order_send({
        'action': mt5.TRADE_ACTION_DEAL,
        'position': p.ticket,
        'symbol': p.symbol,
        'volume': p.volume,
        'type': mt5.ORDER_TYPE_BUY,
        'price': tick.ask,
        'deviation': 50,
        'comment': 'close_unprotected_exchange_mode',
    })
    print(f"Close retcode: {result.retcode}")
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"Profit: ${p.profit:.2f}")
        print("Position closed - unprotected exchange mode position")
else:
    print("Position not found")
mt5.shutdown()
