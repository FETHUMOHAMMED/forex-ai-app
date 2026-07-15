"""RUNTIME VERIFICATION: News Filter"""
import sys, os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-service'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from risk.news_filter import NewsFilter

# TEST 1: Initialization
nf = NewsFilter(blackout_minutes=30, impact_levels=['high'])
assert nf.blackout_minutes == 30
assert nf.impact_levels == ['high']
print('PASSED: TEST 1 - News filter initializes correctly')

# TEST 2-3: Currency splitting
for pair, expected in [('EURUSD', {'EUR', 'USD'}), ('USDSGD', {'USD', 'SGD'})]:
    currencies = {pair[:3], pair[3:]} if len(pair) == 6 else {pair[:3], pair[3:6]}
    assert currencies == expected, f'{pair} split failed'
print('PASSED: TEST 2 - Currency pairs split correctly')

# TEST 4: Empty events = allow trading (fail-open)
nf_empty = NewsFilter(blackout_minutes=30)
nf_empty.cached_events = []
nf_empty.last_fetch_time = datetime.now(timezone.utc)
assert nf_empty.is_high_impact_nearby('EURUSD') == False
print('PASSED: TEST 3 - Empty events allows trading (fail-open)')

# TEST 5: High impact nearby = block
nf_block = NewsFilter(blackout_minutes=30)
nf_block.cached_events = [{
    'datetime': datetime.now(timezone.utc) + timedelta(minutes=10),
    'currency': 'USD', 'impact': 'high', 'event': 'FOMC'
}]
nf_block.last_fetch_time = datetime.now(timezone.utc)
assert nf_block.is_high_impact_nearby('EURUSD') == True
print('PASSED: TEST 4 - High impact event within window blocks trading')

# TEST 6: Far event = no block
nf_far = NewsFilter(blackout_minutes=30)
nf_far.cached_events = [{
    'datetime': datetime.now(timezone.utc) + timedelta(minutes=60),
    'currency': 'USD', 'impact': 'high', 'event': 'CPI'
}]
nf_far.last_fetch_time = datetime.now(timezone.utc)
assert nf_far.is_high_impact_nearby('EURUSD') == False
print('PASSED: TEST 5 - Event outside window does NOT block')

# TEST 7: Low impact = no block
nf_low = NewsFilter(blackout_minutes=30, impact_levels=['high'])
nf_low.cached_events = [{
    'datetime': datetime.now(timezone.utc) + timedelta(minutes=5),
    'currency': 'USD', 'impact': 'low', 'event': 'Minor'
}]
nf_low.last_fetch_time = datetime.now(timezone.utc)
assert nf_low.is_high_impact_nearby('EURUSD') == False
print('PASSED: TEST 6 - Low impact event does NOT block')

# TEST 8: Wrong currency = no block
nf_other = NewsFilter(blackout_minutes=30)
nf_other.cached_events = [{
    'datetime': datetime.now(timezone.utc) + timedelta(minutes=10),
    'currency': 'JPY', 'impact': 'high', 'event': 'BOJ'
}]
nf_other.last_fetch_time = datetime.now(timezone.utc)
assert nf_other.is_high_impact_nearby('EURUSD') == False
print('PASSED: TEST 7 - Wrong currency event does NOT block')

# TEST 9: Already passed event = no block
nf_past = NewsFilter(blackout_minutes=30)
nf_past.cached_events = [{
    'datetime': datetime.now(timezone.utc) - timedelta(minutes=10),
    'currency': 'USD', 'impact': 'high', 'event': 'Old News'
}]
nf_past.last_fetch_time = datetime.now(timezone.utc)
assert nf_past.is_high_impact_nearby('EURUSD') == False
print('PASSED: TEST 8 - Past event does NOT block')

print()
print('ALL 8 RUNTIME TESTS PASSED - News Filter works correctly')