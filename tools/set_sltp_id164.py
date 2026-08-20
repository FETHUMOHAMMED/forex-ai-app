"""Set protective SL/TP on open position 589629837"""
import MetaTrader5 as mt5

mt5.initialize()
position = mt5.positions_get(ticket=589629837)

if position:
    p = position[0]
    entry = p.price_open
    direction = 'SELL' if p.type == 1 else 'BUY'
    
    # Calculate SL/TP (same distances as signal plan: 17.6 pip SL, 2.0 RR = 35.2 pip TP)
    sl_distance = 0.00176  # 17.6 pips
    tp_distance = 0.00352  # 35.2 pips (RR 2.0)
    
    if direction == 'SELL':
        new_sl = entry + sl_distance  # Above entry
        new_tp = entry - tp_distance  # Below entry
    else:
        new_sl = entry - sl_distance  # Below entry
        new_tp = entry + tp_distance  # Above entry
    
    # Modify position with SL/TP
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": p.ticket,
        "sl": round(new_sl, 5),
        "tp": round(new_tp, 5),
    }
    
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"SL/TP SET on position {p.ticket}")
        print(f"  Entry: {entry:.5f}")
        print(f"  SL: {new_sl:.5f} ({'ABOVE' if new_sl > entry else 'BELOW'} entry)")
        print(f"  TP: {new_tp:.5f} ({'BELOW' if new_tp < entry else 'ABOVE'} entry)")
        print(f"  Current profit: ${p.profit:.2f}")
    else:
        print(f"Failed to set SL/TP: retcode={result.retcode if result else 'None'}")
        print(f"  Comment: {result.comment if result else 'N/A'}")
        print(f"  Detail: EURUSDm exchange mode may need different approach")
else:
    print("Position 589629837 not found - may have closed")

mt5.shutdown()
