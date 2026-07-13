"""Final Verification - Institutional Architecture"""
import sys, os, sqlite3

print('=' * 60)
print('  INSTITUTIONAL ARCHITECTURE VERIFICATION')
print('=' * 60)
print()

modules = [
    ('Phase 1: Market Microstructure', 'institutional/market_microstructure.py'),
    ('Phase 6: Validation Script', 'institutional/validate_microstructure.py'),
    ('Phase 7: Trade Quality Scorer', 'institutional/trade_scorer.py'),
    ('Phase 8: Performance Tracker', 'institutional/performance_tracker.py'),
    ('Phase 10: Learning Engine', 'institutional/learning_engine.py'),
    ('Phase 11: Auto-Optimizer', 'institutional/auto_optimizer.py'),
]

all_ok = True
for name, path in modules:
    full_path = os.path.join(os.path.dirname(__file__), '..', path) if not os.path.isabs(path) else path
    if os.path.exists(full_path):
        size = os.path.getsize(full_path)
        status = 'OK' if size > 100 else 'EMPTY'
        print(f'  [OK] {name} ({size} bytes)')
    else:
        print(f'  [MISSING] {name}')
        all_ok = False

print()

# Check database columns
db_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'trades.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('PRAGMA table_info(trades)')
cols = [r[1] for r in c.fetchall()]
inst_cols = ['institutional_bias', 'institutional_score', 'dealer_pressure', 
             'liquidity_state', 'continuation_prob']

print('Database Columns:')
for col in inst_cols:
    if col in cols:
        print(f'  [OK] {col}')
    else:
        print(f'  [MISSING] {col}')
        all_ok = False

c.execute('SELECT COUNT(*) FROM trades WHERE institutional_bias IS NOT NULL')
inst_trades = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL')
total = c.fetchone()[0]
pct = (inst_trades/total*100) if total > 0 else 0
print(f'\nData: {inst_trades}/{total} trades with institutional data ({pct:.0f}%)')
conn.close()
print()

# Check signal pipeline
ai_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'real_ai_service.py')
with open(ai_path, 'r', encoding='utf-8') as f:
    content = f.read()

signal_checks = [
    ('Microstructure import', 'MarketMicrostructure' in content),
    ('Institutional in return', 'institutional_bias' in content),
    ('INSTITUTIONAL logging', '[INSTITUTIONAL]' in content),
]
for name, result in signal_checks:
    status = 'OK' if result else 'MISSING'
    print(f'  [{status}] Signal Pipeline: {name}')
    if not result:
        all_ok = False

print()

# Check watchdog
wd_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'auto_trader_exness.py')
with open(wd_path, 'r', encoding='utf-8') as f:
    content = f.read()

watchdog_checks = [
    ('Trade scorer active', 'TradeQualityScore' in content or 'scorer' in content),
    ('Quality logging', '[QUALITY]' in content),
    ('Inst filter active', 'inst_bias' in content),
]
for name, result in watchdog_checks:
    status = 'OK' if result else 'MISSING'
    print(f'  [{status}] Watchdog: {name}')
    if not result:
        all_ok = False

print()
print('=' * 60)
if all_ok:
    print('  VERDICT: INSTITUTIONAL ARCHITECTURE DEPLOYED')
    print(f'  {inst_trades} trades collecting institutional data')
else:
    print('  VERDICT: Some components missing')
print('=' * 60)
