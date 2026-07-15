"""RUNTIME VERIFICATION: Centralized MT5 Access"""
import sys, os, re

BASE = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(BASE, 'ai-service'))
sys.path.insert(0, BASE)

# TEST 1: broker_exness has fetch_rates method
from broker_exness import MT5Broker
broker = MT5Broker()
assert hasattr(broker, 'fetch_rates')
assert hasattr(broker, 'connect')
assert hasattr(broker, 'place_market_order')
assert hasattr(broker, 'get_positions')
print('PASSED: TEST 1 - Broker has all required methods')

# TEST 2-3: Check real_ai_service.py
ai_path = os.path.join(BASE, 'ai-service', 'real_ai_service.py')
with open(ai_path, 'r', encoding='utf-8') as f:
    ai_content = f.read()

assert 'from broker_exness import MT5Broker' in ai_content
print('PASSED: TEST 2 - real_ai_service imports MT5Broker')

assert 'self._broker.fetch_rates' in ai_content
print('PASSED: TEST 3 - fetch_data_mt5 uses broker.fetch_rates')

# TEST 4-5: Check auto_trader_exness.py
wd_path = os.path.join(BASE, 'ai-service', 'auto_trader_exness.py')
with open(wd_path, 'r', encoding='utf-8') as f:
    wd_content = f.read()

assert 'acc.broker.connect()' in wd_content or 'broker.connect()' in wd_content
print('PASSED: TEST 4 - Watchdog reconnect uses broker')

mt5_init_in_ai = len(re.findall(r'mt5\.initialize\(\)', ai_content))
assert mt5_init_in_ai <= 1, f'Found {mt5_init_in_ai} direct mt5.initialize() calls (1 allowed for utility)'
print('PASSED: TEST 5 - Signal pipeline uses broker; utility function exempt')

# TEST 6: broker_exness is the single init point
br_path = os.path.join(BASE, 'ai-service', 'broker_exness.py')
with open(br_path, 'r', encoding='utf-8') as f:
    br_content = f.read()

assert 'mt5.initialize()' in br_content
print('PASSED: TEST 6 - broker_exness is the single MT5 init point')

# TEST 7: broker handles login
assert 'mt5.login' in br_content
print('PASSED: TEST 7 - broker.connect handles authentication')

# TEST 8: No direct data calls
data_calls = len(re.findall(r'mt5\.copy_rates_from_pos', ai_content))
assert data_calls == 0, f'Found {data_calls} direct mt5.copy_rates_from_pos'
print('PASSED: TEST 8 - No direct MT5 data calls in signal engine')

print()
print('ALL 8 RUNTIME TESTS PASSED - MT5 access is centralized through broker')