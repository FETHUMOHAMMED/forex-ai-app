content = open('ai-service/broker_exness.py').read()

# Add is_exchange definition before the order_send call
old = '            result = mt5.order_send(request)'
new = '''            # Check if symbol uses exchange mode (trade_mode=4)
            trade_mode = symbol_info.trade_mode if symbol_info else 0
            is_exchange = (trade_mode == 4)  # SYMBOL_TRADE_MODE_EXCHANGE

            result = mt5.order_send(request)'''

if old in content:
    content = content.replace(old, new, 1)  # Only first occurrence
    open('ai-service/broker_exness.py', 'w').write(content)
    print('Fixed: is_exchange is now defined before use')
else:
    print('Pattern not found - checking file...')
