import json
with open('ai-service/config.json') as f:
    c = json.load(f)
for a in c['accounts']:
    if a['name'] == 'Demo2':
        print('=== Demo2 Config ===')
        print('pairs: ' + str(a['pairs']))
        print('min_confidence: ' + str(a['min_confidence']))
        print('risk_percent: ' + str(a['risk_percent']))
        print('sessions_enabled: ' + str(a.get('sessions_enabled', [])))
        print('max_daily_trades: ' + str(a.get('max_daily_trades', 'N/A')))

print()
print('EURUSD session_hours: ' + str(c['session_hours'].get('EURUSD', 'NOT SET')))

# Verify each value
for a in c['accounts']:
    if a['name'] == 'Demo2':
        checks = [
            ('pairs', a['pairs'] == ['EURUSD']),
            ('confidence', a['min_confidence'] == 0.6),
            ('risk', a['risk_percent'] == 0.05),
            ('sessions', a.get('sessions_enabled') == ['LONDON']),
            ('hours', c['session_hours'].get('EURUSD') == [[7, 17]])
        ]
        all_ok = all(c[1] for c in checks)
        print('\nChecks:')
        for name, result in checks:
            print('  ' + name + ': ' + ('PASS' if result else 'FAIL'))
        print('\nALL V3 CONFIG: ' + ('PASS' if all_ok else 'FAIL'))
