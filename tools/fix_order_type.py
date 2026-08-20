"""Update auto_trader to use pending orders (SL/TP works in exchange mode)"""
path = 'ai-service/auto_trader_exness.py'
content = open(path, 'r', encoding='utf-8', errors='replace').read()

# For SELL signals: use ORDER_TYPE_SELL_LIMIT instead of ORDER_TYPE_SELL
# For BUY signals: use ORDER_TYPE_BUY_LIMIT instead of ORDER_TYPE_BUY
content = content.replace(
    'request_type = mt5.ORDER_TYPE_SELL',
    'request_type = mt5.ORDER_TYPE_SELL_LIMIT'
)
content = content.replace(
    'request_type = mt5.ORDER_TYPE_BUY',
    'request_type = mt5.ORDER_TYPE_BUY_LIMIT'
)

# Change action from DEAL to PENDING for exchange mode
content = content.replace(
    '"action": mt5.TRADE_ACTION_DEAL,',
    '"action": mt5.TRADE_ACTION_PENDING,'
)

open(path, 'w', encoding='utf-8').write(content)
print('Updated auto_trader to use pending orders with SL/TP')
print('This allows SL/TP protection on exchange-mode symbols')
