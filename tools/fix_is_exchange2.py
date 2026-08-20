content = open('ai-service/broker_exness.py', encoding='utf-8', errors='replace').read()

old = '            result = mt5.order_send(request)'
new = '''            # Check if symbol uses exchange mode (trade_mode=4)
            trade_mode = symbol_info.trade_mode if symbol_info else 0
            is_exchange = (trade_mode == 4)  # SYMBOL_TRADE_MODE_EXCHANGE

            result = mt5.order_send(request)'''

if old in content:
    content = content.replace(old, new, 1)
    open('ai-service/broker_exness.py', 'w', encoding='utf-8').write(content)
    print('Fixed: is_exchange defined')
else:
    print('Pattern not found')
