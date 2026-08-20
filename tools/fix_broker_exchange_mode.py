"""Fix broker_exness.py for exchange-mode symbols (EURUSDm)"""
import sys
from pathlib import Path

broker_path = Path("ai-service/broker_exness.py")

with open(broker_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the order request and modify it to handle exchange mode
old_request = '''            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": request_type,
                "price": price,
                "sl": sl,
                "tp": tp,'''

new_request = '''            # For exchange-mode symbols (trade_mode=4), SL/TP must be set AFTER opening
            trade_mode = symbol_info.trade_mode if symbol_info else 0
            is_exchange = (trade_mode == 4)  # SYMBOL_TRADE_MODE_EXCHANGE
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": request_type,
                "price": price,
                "deviation": deviation,
                "magic": 234000,
                "comment": f"AI_trade_conf{confidence:.2f}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": fill_type,
            }
            
            # Only include SL/TP for non-exchange mode symbols
            if not is_exchange:
                request["sl"] = sl
                request["tp"] = tp'''

if old_request in content:
    content = content.replace(old_request, new_request)
    
    # Also need to handle setting SL/TP after order for exchange mode
    # Find the result handling section
    old_result = '''            result = mt5.order_send(request)
            print(f"[MT5 ORDER] {symbol} retcode={result.retcode if result else 'None'} comment={result.comment if result else 'N/A'} order={result.order if result else 'N/A'}")'''
    
    new_result = '''            result = mt5.order_send(request)
            print(f"[MT5 ORDER] {symbol} retcode={result.retcode if result else 'None'} comment={result.comment if result else 'N/A'} order={result.order if result else 'N/A'}")
            
            # For exchange-mode symbols, set SL/TP after position is opened
            if is_exchange and result and result.retcode == mt5.TRADE_RETCODE_DONE:
                positions = mt5.positions_get(symbol=symbol)
                if positions:
                    pos = max(positions, key=lambda p: p.ticket)
                    modify_request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": pos.ticket,
                        "sl": sl,
                        "tp": tp
                    }
                    modify_result = mt5.order_send(modify_request)
                    if modify_result and modify_result.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"[SLTP SET] {symbol} SL={sl:.5f} TP={tp:.5f}")
                    else:
                        print(f"[SLTP FAIL] {symbol} retcode={modify_result.retcode if modify_result else 'None'}")'''
    
    if old_result in content:
        content = content.replace(old_result, new_result)
    
    # Backup
    import shutil
    shutil.copy2(broker_path, broker_path.with_suffix('.py.bak2'))
    
    with open(broker_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed broker_exness.py for exchange-mode symbols")
    print("SL/TP are now set AFTER opening for EURUSDm")
    print("Daemon restart required")
else:
    print("Could not find the request pattern - it may already be fixed differently")
    print("Check if the old request pattern matches:")
    # Show what's around line 148
    lines = content.split('\n')
    for i in range(140, 170):
        if i < len(lines):
            print(f"{i+1}: {lines[i]}")
