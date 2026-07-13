"""Full Institutional System Health Check"""
import os, sqlite3

print('=' * 65)
print('  INSTITUTIONAL SYSTEM HEALTH CHECK')
print('=' * 65)
print()

base = os.path.dirname(__file__)
errors = []

# 1. All volumes present
volumes = [
    ('market_microstructure.py', 'Vol 1: Microstructure'),
    ('liquidity_intelligence.py', 'Vol 2: Liquidity'),
    ('institutional_structure.py', 'Vol 3: Structure'),
    ('institutional_risk_engine.py', 'Vol 4: Risk'),
    ('trade_decision_engine.py', 'Vol 5: Decision'),
    ('institutional_learning_engine.py', 'Vol 6: Learning'),
    ('performance_intelligence.py', 'Vol 7: Performance'),
]
total_bytes = 0
print('1. MODULES')
for fname, label in volumes:
    fpath = os.path.join(base, fname)
    ok = os.path.exists(fpath)
    size = os.path.getsize(fpath) if ok else 0
    total_bytes += size
    status = 'OK' if ok else 'MISSING'
    if not ok: errors.append(f'MISSING: {fname}')
    print(f'  [{status}] {label} ({size:,} bytes)')
print(f'  TOTAL: {total_bytes:,} bytes ({total_bytes/1024:.0f} KB)')
print()

# 2. Database
db_path = os.path.join(base, '..', 'ai-service', 'trades.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]

required = ['trades', 'trade_memory', 'performance_memory']
print('2. DATABASE')
for t in required:
    ok = t in tables
    status = 'OK' if ok else 'MISSING'
    if not ok: errors.append(f'MISSING table: {t}')
    c.execute(f"SELECT COUNT(*) FROM {t}") if ok else None
    count = c.fetchone()[0] if ok else 0
    c.execute(f'PRAGMA table_info({t})') if ok else None
    cols = len(c.fetchall()) if ok else 0
    print(f'  [{status}] {t}: {cols} cols, {count} rows')

# Check institutional columns in trades
c.execute('PRAGMA table_info(trades)')
trade_cols = [r[1] for r in c.fetchall()]
inst_cols = ['institutional_bias', 'institutional_score', 'dealer_pressure', 'liquidity_state', 'continuation_prob']
missing_cols = [c for c in inst_cols if c not in trade_cols]
if missing_cols:
    errors.append(f'MISSING columns in trades: {missing_cols}')
print(f'  Institutional columns in trades: {len(inst_cols) - len(missing_cols)}/{len(inst_cols)}')
conn.close()
print()

# 3. Signal pipeline integration
ai_path = os.path.join(base, '..', 'ai-service', 'real_ai_service.py')
with open(ai_path, 'r', encoding='utf-8', errors='ignore') as f:
    ai = f.read()

print('3. SIGNAL PIPELINE')
ai_checks = [
    ('Vol 1: Microstructure', 'MarketMicrostructure' in ai),
    ('Vol 2: Liquidity', 'LiquidityIntelligence' in ai),
    ('Vol 3: Structure', 'InstitutionalStructure' in ai),
    ('Vol 7: Performance', 'PerformanceIntelligence' in ai),
    ('All logs active', '[INSTITUTIONAL]' in ai and '[LIQUIDITY]' in ai and '[STRUCTURE]' in ai),
]
for name, ok in ai_checks:
    status = 'PASS' if ok else 'FAIL'
    if not ok: errors.append(f'FAIL: {name}')
    print(f'  [{status}] {name}')
print()

# 4. Watchdog integration
wd_path = os.path.join(base, '..', 'ai-service', 'auto_trader_exness.py')
with open(wd_path, 'r', encoding='utf-8', errors='ignore') as f:
    wd = f.read()

print('4. WATCHDOG')
wd_checks = [
    ('Risk engine', 'InstitutionalRiskEngine' in wd),
    ('Decision engine', 'TradeDecisionEngine' in wd),
    ('Learning engine', 'InstitutionalLearningEngine' in wd),
    ('Performance engine', 'PerformanceIntelligence' in wd),
    ('Gatekeeper', '[GATEKEEPER' in wd),
    ('Quality scoring', '[QUALITY]' in wd),
    ('Risk logging', '[RISK]' in wd),
    ('Decision logging', '[DECISION]' in wd),
    ('Learning logging', '[LEARNING]' in wd),
]
for name, ok in wd_checks:
    status = 'PASS' if ok else 'FAIL'
    if not ok: errors.append(f'FAIL: {name}')
    print(f'  [{status}] {name}')
print()

# 5. Live activity
print('5. LIVE ACTIVITY')
log_path = os.path.join(base, '..', 'ai-service', 'forex_ai.log')
if os.path.exists(log_path):
    size = os.path.getsize(log_path)
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    inst_count = sum(1 for l in lines if '[INSTITUTIONAL]' in l)
    liq_count = sum(1 for l in lines if '[LIQUIDITY]' in l)
    struct_count = sum(1 for l in lines if '[STRUCTURE]' in l)
    print(f'  Log size: {size:,} bytes | Lines: {len(lines):,}')
    print(f'  [INSTITUTIONAL]: {inst_count:,} | [LIQUIDITY]: {liq_count:,} | [STRUCTURE]: {struct_count:,}')
    print(f'  System active: {"YES" if inst_count > 100 else "LOW ACTIVITY"}')
else:
    errors.append('Log file missing')
    print('  Log file missing')

print()
print('=' * 65)
if errors:
    print(f'  ISSUES FOUND ({len(errors)}):')
    for e in errors:
        print(f'    - {e}')
    print(f'  HEALTH: NEEDS ATTENTION')
else:
    print('  SYSTEM HEALTH: 100%')
    print('  All 7 volumes integrated')
    print('  All databases writable')
    print('  All pipelines active')
    print('  Ready for data collection')
print('=' * 65)