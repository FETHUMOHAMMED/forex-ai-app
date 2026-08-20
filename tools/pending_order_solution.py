"""Pending Order Solution - Sets SL/TP at order creation (works with exchange mode)"""
import MetaTrader5 as mt5

mt5.initialize()

# For a SELL signal at 1.15590:
entry_price = 1.15590
sl_price = 1.15766    # 17.6 pips above entry
tp_price = 1.15238    # 35.2 pips below entry (RR 2.0)

# Use SELL_STOP pending order (for entry below current market)
request = {
    "action": mt5.TRADE_ACTION_PENDING,
    "symbol": "EURUSDm",
    "volume": 0.01,
    "type": mt5.ORDER_TYPE_SELL_STOP,
    "price": entry_price,
    "sl": sl_price,
    "tp": tp_price,
    "deviation": 30,
    "magic": 234000,
    "comment": "V3_SELL_STOP_with_SLTP",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_RETURN,
}

result = mt5.order_send(request)
if result and result.retcode == mt5.TRADE_RETCODE_DONE:
    print(f"PENDING ORDER PLACED with SL/TP!")
    print(f"  Order: {result.order}")
    print(f"  Entry: {entry_price}")
    print(f"  SL: {sl_price}")
    print(f"  TP: {tp_price}")
elif result:
    print(f"Failed: retcode={result.retcode} comment={result.comment}")
    # Try with BUY_STOP for BUY signals
    print("Trying alternative: SELL_LIMIT")
    request["type"] = mt5.ORDER_TYPE_SELL_LIMIT
    result2 = mt5.order_send(request)
    if result2 and result2.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"PENDING ORDER (SELL_LIMIT) PLACED with SL/TP!")
    else:
        print(f"SELL_LIMIT also failed: retcode={result2.retcode if result2 else 'None'}")

mt5.shutdown()
