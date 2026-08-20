# Fix the SIZE test case that has too many elements
content = open('tools/verify_execution_gate.py').read()

# Fix the SIZE test case - remove the extra None
old = '''    ("SIZE", "Volume too large",
     {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD'},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, [],
     None),  # Size is hardcoded 0.01 in gate'''

new = '''    ("SIZE", "Volume too large (tested via volume=1.0)",
     {'age_seconds': 10, 'entry': 1.15542, 'stop_loss': 1.15718, 'take_profit': 1.15190, 'direction': 'SELL', 'pair': 'EURUSD', 'volume': 1.0},
     {'bid': 1.15542, 'ask': 1.15550, 'spread': 0.0008, 'mt5_connected': True},
     {'equity': 5000, 'risk_pct': 0.0005, 'account_id': REDACTED_LIVE_ACCOUNT}, []),'''

content = content.replace(old, new)
open('tools/verify_execution_gate.py', 'w').write(content)
print('Fixed SIZE test case')
