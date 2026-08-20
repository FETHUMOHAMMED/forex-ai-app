import MetaTrader5 as mt5
mt5.initialize()
for sym in ["EURUSDm", "EURUSD", "EURUSD.", "EURUSDpro"]:
    mt5.symbol_select(sym, True)
    info = mt5.symbol_info(sym)
    if info:
        print(f"{sym}: tick_value={info.trade_tick_value} tick_size={info.trade_tick_size} point={info.point} vol_min={info.volume_min}")
        pip_val = (info.trade_tick_value / info.trade_tick_size) * info.point * 10
        print(f"  pip value per lot: ${pip_val:.2f}")
        print(f"  pip value per 0.01: ${pip_val*0.01:.2f}")
        print(f"  Risk 17.6 pip SL @ 0.01: ${pip_val*0.01*17.6:.2f}")
        break
    else:
        print(f"{sym}: not available")
mt5.shutdown()
