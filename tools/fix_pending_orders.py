# Fix broker_exness.py to use LIMIT orders
content = open('ai-service/broker_exness.py', encoding='utf-8', errors='replace').read()

# Replace market order types with pending order types
content = content.replace(
    'request_type = mt5.ORDER_TYPE_BUY',
    'request_type = mt5.ORDER_TYPE_BUY_LIMIT'
)
content = content.replace(
    'request_type = mt5.ORDER_TYPE_SELL',
    'request_type = mt5.ORDER_TYPE_SELL_LIMIT'
)

# Fix the action from DEAL to PENDING
content = content.replace(
    '"action": mt5.TRADE_ACTION_DEAL,',
    '"action": mt5.TRADE_ACTION_PENDING,'
)

open('ai-service/broker_exness.py', 'w', encoding='utf-8').write(content)
print('Fixed broker_exness.py: LIMIT orders + PENDING action')
