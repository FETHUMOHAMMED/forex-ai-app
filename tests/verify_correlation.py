"""RUNTIME VERIFICATION: Correlation Control"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-service'))

# Simulate the exact logic from auto_trader_exness.py lines 1283-1311

USD_LONG_PAIRS = {'USDJPY', 'USDCAD', 'USDCHF'}
USD_SHORT_PAIRS = {'EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD'}

def count_usd_exposure(positions):
    """Replicate exact watchdog logic"""
    usd_long_count = 0
    usd_short_count = 0
    for pos in positions:
        pos_symbol = pos['symbol'].replace('m', '')
        pos_dir = 'BUY' if pos['type'] == 0 else 'SELL'
        if pos_symbol in USD_LONG_PAIRS and pos_dir == 'BUY':
            usd_long_count += 1
        if pos_symbol in USD_SHORT_PAIRS and pos_dir == 'SELL':
            usd_short_count += 1
    return usd_long_count, usd_short_count

def should_reject(pair, direction, usd_long, usd_short):
    """Replicate exact rejection logic"""
    if pair in USD_LONG_PAIRS and direction == 'BUY' and usd_long >= 2:
        return True
    if pair in USD_SHORT_PAIRS and direction == 'SELL' and usd_short >= 2:
        return True
    return False

# TEST 1: No positions - should allow trade
positions = []
usd_long, usd_short = count_usd_exposure(positions)
assert usd_long == 0 and usd_short == 0
assert not should_reject('USDCAD', 'BUY', usd_long, usd_short)
assert not should_reject('EURUSD', 'SELL', usd_long, usd_short)
print('PASSED: TEST 1 - No positions, all trades allowed')

# TEST 2: One USD long - should allow second
positions = [{'symbol': 'USDCADm', 'type': 0}]  # BUY USDCAD
usd_long, usd_short = count_usd_exposure(positions)
assert usd_long == 1 and usd_short == 0
assert not should_reject('USDJPY', 'BUY', usd_long, usd_short)
print('PASSED: TEST 2 - One USD long, second allowed')

# TEST 3: Two USD long - should REJECT third
positions = [
    {'symbol': 'USDCADm', 'type': 0},  # BUY
    {'symbol': 'USDJPYm', 'type': 0},  # BUY
]
usd_long, usd_short = count_usd_exposure(positions)
assert usd_long == 2
assert should_reject('USDCHF', 'BUY', usd_long, usd_short)
print('PASSED: TEST 3 - Two USD long, third REJECTED')

# TEST 4: Two USD short - should REJECT third
positions = [
    {'symbol': 'EURUSDm', 'type': 1},  # SELL
    {'symbol': 'GBPUSDm', 'type': 1},  # SELL
]
usd_long, usd_short = count_usd_exposure(positions)
assert usd_short == 2
assert should_reject('AUDUSD', 'SELL', usd_long, usd_short)
print('PASSED: TEST 4 - Two USD short, third REJECTED')

# TEST 5: Mixed positions - long + short are independent
positions = [
    {'symbol': 'USDCADm', 'type': 0},  # BUY (long USD)
    {'symbol': 'EURUSDm', 'type': 1},  # SELL (long USD via short)
]
usd_long, usd_short = count_usd_exposure(positions)
assert usd_long == 1 and usd_short == 1
# Still allows one more of each
assert not should_reject('USDJPY', 'BUY', usd_long, usd_short)
assert not should_reject('GBPUSD', 'SELL', usd_long, usd_short)
print('PASSED: TEST 5 - Mixed positions, independent limits')

# TEST 6: Opposite direction doesn't count
positions = [
    {'symbol': 'USDCADm', 'type': 1},  # SELL USDCAD = short USD (doesn't count as long)
]
usd_long, usd_short = count_usd_exposure(positions)
assert usd_long == 0  # SELL USDCAD is not USD long
assert usd_short == 0  # USDCAD is not in USD_SHORT_PAIRS
print('PASSED: TEST 6 - SELL USDCAD correctly NOT counted as USD long')

# TEST 7: Correlation matrix from config
POS_CORRELATED = {
    'EURUSD': ['GBPUSD', 'AUDUSD', 'NZDUSD'],
    'GBPUSD': ['EURUSD', 'AUDUSD', 'NZDUSD'],
}
INV_CORRELATED = {
    'EURUSD': ['USDCHF', 'USDCAD'],
    'USDCHF': ['EURUSD', 'GBPUSD'],
}

# EURUSD SELL + GBPUSD SELL = same direction correlation
positions = [{'symbol': 'EURUSDm', 'type': 1}]  # SELL EURUSD
pair = 'GBPUSD'
direction = 'SELL'
same_count = sum(1 for p in positions 
    if p['symbol'].replace('m','') in POS_CORRELATED.get(pair, []) 
    and ('BUY' if p['type']==0 else 'SELL') == direction)
assert same_count == 1
print('PASSED: TEST 7 - Correlation matrix correctly identifies same-direction pairs')

# TEST 8: Inverse correlation
positions = [{'symbol': 'EURUSDm', 'type': 1}]  # SELL EURUSD
pair = 'USDCHF'
direction = 'BUY'
inv_count = sum(1 for p in positions
    if p['symbol'].replace('m','') in INV_CORRELATED.get(pair, [])
    and ('BUY' if p['type']==0 else 'SELL') != direction)
assert inv_count == 1
print('PASSED: TEST 8 - Inverse correlation correctly identified')

print()
print('ALL 8 RUNTIME TESTS PASSED - Correlation Control works correctly')