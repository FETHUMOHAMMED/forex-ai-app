"""Fix auto-trader to use PENDING orders (supports SL/TP on exchange mode)"""
content = open('ai-service/auto_trader_exness.py', 'r', encoding='utf-8', errors='replace').read()

# Change TRADE_ACTION_DEAL to TRADE_ACTION_PENDING
content = content.replace(
    '"action": mt5.TRADE_ACTION_DEAL,',
    '"action": mt5.TRADE_ACTION_PENDING,'
)

# Change ORDER_TYPE_SELL to ORDER_TYPE_SELL_LIMIT
content = content.replace(
    'request_type = mt5.ORDER_TYPE_SELL',
    'request_type = mt5.ORDER_TYPE_SELL_LIMIT'
)
content = content.replace(
    'request_type = mt5.ORDER_TYPE_BUY',
    'request_type = mt5.ORDER_TYPE_BUY_LIMIT'
)

open('ai-service/auto_trader_exness.py', 'w', encoding='utf-8').write(content)
print('Fixed: auto_trader now uses pending orders with SL/TP')
