import MetaTrader5 as mt5
mt5.initialize()
info = mt5.symbol_info('EURUSD')
if info:
    print(f"tick_value: {info.trade_tick_value}")
    print(f"tick_size: {info.trade_tick_size}")
    print(f"point: {info.point}")
    print(f"volume_min: {info.volume_min}")
    print(f"volume_step: {info.volume_step}")
    
    pip_val_per_lot = (info.trade_tick_value / info.trade_tick_size) * info.point * 10
    print(f"pip value per standard lot: ${pip_val_per_lot:.2f}")
    print(f"pip value per 0.01 lot: ${pip_val_per_lot * 0.01:.2f}")
    
    sl_distance = 17.6
    risk = pip_val_per_lot * 0.01 * sl_distance
    print(f"Risk for 0.01 lot, 17.6 pip SL: ${risk:.2f}")
    print(f"Risk as pct of $19.06: {risk/19.06*100:.1f}%")
    
    # What balance needed for 0.05% risk with this setup?
    required_balance = risk / 0.0005
    print(f"Balance needed for 0.05pct risk: ${required_balance:,.0f}")
mt5.shutdown()
