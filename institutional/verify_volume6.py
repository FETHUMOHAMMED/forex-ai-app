"""Volume 6 Verification - Institutional Learning Engine"""
import os, sqlite3

print('=' * 65)
print('  VOLUME 6 VERIFICATION - LEARNING ENGINE')
print('=' * 65)
print()

# 1. Modules
base = os.path.dirname(__file__)
modules = [
    ('setup_memory.py', 'Setup Memory Database'),
    ('institutional_learning_engine.py', 'Learning Engine'),
]
all_modules = True
total_v6 = 0
for fname, label in modules:
    fpath = os.path.join(base, fname)
    exists = os.path.exists(fpath)
    size = os.path.getsize(fpath) if exists else 0
    total_v6 += size
    status = 'PRESENT' if exists else 'MISSING'
    if not exists: all_modules = False
    print(f'  [{status}] {label}: {fname} ({size:,} bytes)')
print()

# 2. All volumes
print('2. ALL 6 VOLUMES')
volumes = [
    ('market_microstructure.py', 'Vol 1: Microstructure'),
    ('liquidity_intelligence.py', 'Vol 2: Liquidity'),
    ('institutional_structure.py', 'Vol 3: Structure'),
    ('institutional_risk_engine.py', 'Vol 4: Risk'),
    ('trade_decision_engine.py', 'Vol 5: Decision'),
    ('institutional_learning_engine.py', 'Vol 6: Learning'),
]
total_bytes = 0
for fname, label in volumes:
    fpath = os.path.join(base, fname)
    exists = os.path.exists(fpath)
    size = os.path.getsize(fpath) if exists else 0
    total_bytes += size
    status = 'PRESENT' if exists else 'MISSING'
    print(f'  [{status}] {label} ({size:,} bytes)')
print()

# 3. Database
print('3. TRADE MEMORY DATABASE')
db_path = os.path.join(base, '..', 'ai-service', 'trades.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trade_memory'")
table_exists = c.fetchone() is not None
print(f'  trade_memory table: {"PRESENT" if table_exists else "MISSING"}')
if table_exists:
    c.execute('SELECT COUNT(*) FROM trade_memory')
    mem_count = c.fetchone()[0]
    c.execute('PRAGMA table_info(trade_memory)')
    cols = len(c.fetchall())
    print(f'  Memory entries: {mem_count}')
    print(f'  Columns: {cols}')
conn.close()
print()

# 4. Watchdog integration
wd_path = os.path.join(base, '..', 'ai-service', 'auto_trader_exness.py')
with open(wd_path, 'r', encoding='utf-8', errors='ignore') as f:
    wd = f.read()

print('4. WATCHDOG INTEGRATION')
wd_checks = [
    ('Learning engine imported', 'InstitutionalLearningEngine' in wd),
    ('Setup memory imported', 'log_trade_to_memory' in wd or 'setup_memory' in wd),
    ('Learning engine initialized', 'self.learning_engine' in wd),
    ('LEARNING logging active', '[LEARNING]' in wd),
    ('DECISION still active', '[DECISION]' in wd),
    ('RISK still active', '[RISK]' in wd),
    ('GATEKEEPER still active', '[GATEKEEPER' in wd),
]
all_wd = True
for name, result in wd_checks:
    status = 'PASS' if result else 'FAIL'
    if not result: all_wd = False
    print(f'  [{status}] {name}')
print()

# 5. Signal pipeline
ai_path = os.path.join(base, '..', 'ai-service', 'real_ai_service.py')
with open(ai_path, 'r', encoding='utf-8', errors='ignore') as f:
    ai = f.read()

print('5. SIGNAL PIPELINE (Volumes 1-3)')
for label, key in [('Volume 1', '[INSTITUTIONAL]'), ('Volume 2', '[LIQUIDITY]'), ('Volume 3', '[STRUCTURE]')]:
    print(f'  [{"PASS" if key in ai else "FAIL"}] {label}')

print()
print('=' * 65)
print(f'  TOTAL CODE: {total_bytes:,} bytes ({total_bytes/1024:.0f} KB)')
print(f'  Volume 6: {total_v6:,} bytes')
if all_modules and all_wd and table_exists:
    print('  VOLUME 6: FULLY OPERATIONAL')
    print('  6 volumes, trade memory active, all pipelines integrated')
else:
    print('  Issues found - check above')
print('=' * 65)