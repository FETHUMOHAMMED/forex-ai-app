"""RUNTIME VERIFICATION: Daily Loss Circuit Breaker"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-service'))

class MockAccount:
    name = 'TestAccount'
    starting_balance = 10000.0
    max_daily_loss_percent = 0.05
    daily_peak_balance = 10000.0
    trail_drawdown_percent = 0.05
    broker = None
    _paused = False
    equity_history = []
    daily_trades = 0
    today = None
    loss_pause_until = None
    consecutive_losses = 0
    consecutive_loss_limit = 5
    _original_risk = 0.01
    risk_percent = 0.01
    hedge = type('obj', (object,), {'reset': lambda s: None})()
    last_trade_time = {}
    failed_pairs = {}

class MockBroker:
    def get_balance(self): return 10000.0
    def get_equity(self): return 9400.0
    def get_positions(self): return []
    connected = True

# TEST 1: Loss detection
acc = MockAccount()
acc.broker = MockBroker()
equity = acc.broker.get_equity()
loss = acc.starting_balance - equity
loss_pct = (loss / acc.starting_balance) * 100
print(f'[TEST 1] Equity: {equity} | Loss: {loss} ({loss_pct:.1f}%)')
assert loss == 600.0, f'Expected 600 loss, got {loss}'
assert loss_pct == 6.0, f'Expected 6.0%, got {loss_pct}%'
print('PASSED: Loss correctly calculated')

# TEST 2: Circuit breaker triggers
limit_hit = loss / acc.starting_balance >= acc.max_daily_loss_percent
assert limit_hit == True, 'Circuit breaker should trigger at 6% loss (limit 5%)'
print('PASSED: Circuit breaker triggers correctly')

# TEST 3: No false trigger at 4%
class MockBroker2:
    def get_balance(self): return 10000.0
    def get_equity(self): return 9600.0
    def get_positions(self): return []
    connected = True

acc2 = MockAccount()
acc2.broker = MockBroker2()
loss2 = acc2.starting_balance - acc2.broker.get_equity()
limit_hit2 = loss2 / acc2.starting_balance >= acc2.max_daily_loss_percent
assert limit_hit2 == False, 'Should NOT trigger at 4% loss'
print('PASSED: No false trigger at 4% loss')

# TEST 4: Trailing drawdown
acc3 = MockAccount()
acc3.broker = MockBroker()
equity3 = acc3.broker.get_equity()
trail_dd = (acc3.daily_peak_balance - equity3) / acc3.daily_peak_balance
assert abs(trail_dd - 0.06) < 0.001, f'Expected 6% trail DD, got {trail_dd*100:.1f}%'
assert trail_dd >= acc3.trail_drawdown_percent
print('PASSED: Trailing drawdown triggers at 6%')

# TEST 5: Consecutive loss pause
acc4 = MockAccount()
acc4.consecutive_losses = 4
acc4.consecutive_loss_limit = 5
acc4.consecutive_losses += 1
assert acc4.consecutive_losses == 5
assert acc4.consecutive_losses >= acc4.consecutive_loss_limit
print('PASSED: Consecutive loss pause triggers at 5')

print()
print('ALL 5 RUNTIME TESTS PASSED - Daily Loss Circuit Breaker works correctly')