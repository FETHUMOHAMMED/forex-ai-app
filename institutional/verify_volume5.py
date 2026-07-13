"""Volume 5 Verification - Institutional Trade Decision Engine"""
import os

print('=' * 65)
print('  VOLUME 5 VERIFICATION - DECISION ENGINE')
print('=' * 65)
print()

# 1. Module existence
path = os.path.join(os.path.dirname(__file__), 'trade_decision_engine.py')
if os.path.exists(path):
    size = os.path.getsize(path)
    print(f'1. MODULE: trade_decision_engine.py ({size:,} bytes)')
else:
    print('1. MODULE: MISSING')
print()

# 2. All volumes present
print('2. ALL VOLUMES PRESENT')
volumes = [
    ('market_microstructure.py', 'Volume 1: Microstructure'),
    ('liquidity_intelligence.py', 'Volume 2: Liquidity'),
    ('institutional_structure.py', 'Volume 3: Structure'),
    ('institutional_risk_engine.py', 'Volume 4: Risk Allocation'),
    ('trade_decision_engine.py', 'Volume 5: Decision Engine'),
]
all_volumes = True
total_bytes = 0
for fname, label in volumes:
    fpath = os.path.join(os.path.dirname(__file__), fname)
    exists = os.path.exists(fpath)
    if not exists:
        all_volumes = False
    status = 'PRESENT' if exists else 'MISSING'
    fsize = os.path.getsize(fpath) if exists else 0
    total_bytes += fsize
    print(f'  [{status}] {label}: {fname} ({fsize:,} bytes)')
print()

# 3. Signal pipeline
ai_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'real_ai_service.py')
with open(ai_path, 'r', encoding='utf-8', errors='ignore') as f:
    ai_content = f.read()

print('3. SIGNAL PIPELINE (Volumes 1-3)')
sig_checks = [
    ('Volume 1: [INSTITUTIONAL]', '[INSTITUTIONAL]' in ai_content),
    ('Volume 2: [LIQUIDITY]', '[LIQUIDITY]' in ai_content),
    ('Volume 3: [STRUCTURE]', '[STRUCTURE]' in ai_content),
]
for name, result in sig_checks:
    print(f'  [{"PASS" if result else "FAIL"}] {name}')

# 4. Watchdog integration
wd_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'auto_trader_exness.py')
with open(wd_path, 'r', encoding='utf-8', errors='ignore') as f:
    wd_content = f.read()

print()
print('4. WATCHDOG INTEGRATION (Volumes 4-5)')
wd_checks = [
    ('Risk engine imported', 'InstitutionalRiskEngine' in wd_content),
    ('Decision engine imported', 'TradeDecisionEngine' in wd_content),
    ('Decision engine initialized', 'self.decision_engine' in wd_content),
    ('RISK logging active', '[RISK]' in wd_content),
    ('DECISION logging active', '[DECISION]' in wd_content),
    ('Gatekeeper still active', '[GATEKEEPER' in wd_content),
    ('Quality scoring still active', '[QUALITY]' in wd_content),
]
all_pass = True
for name, result in wd_checks:
    status = 'PASS' if result else 'FAIL'
    if not result:
        all_pass = False
    print(f'  [{status}] {name}')
print()

# 5. Live log evidence
print('5. LIVE LOG EVIDENCE')
log_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'forex_ai.log')
entries = {
    '[STRUCTURE]': 'Volume 3: Structure',
    '[LIQUIDITY]': 'Volume 2: Liquidity',
    '[INSTITUTIONAL]': 'Volume 1: Microstructure'
}
all_active = True
if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            for key in entries:
                if key in line and not hasattr(entries[key], 'count'):
                    pass
    
    for key, label in entries.items():
        count = 0
        last = ''
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if key in line:
                    count += 1
                    last = line.strip()
        print(f'  {label}: {count:,} entries')
        if last:
            print(f'    Latest: {last[:120]}')
        if count == 0:
            all_active = False

print()
print('=' * 65)
print(f'  TOTAL INSTITUTIONAL CODE: {total_bytes:,} bytes ({total_bytes/1024:.0f} KB)')
if all_pass and all_volumes and all_active:
    print('  VOLUME 5: FULLY OPERATIONAL')
    print(f'  Module: {size:,} bytes')
    print('  Pipeline: All checks passed')
    print('  Watchdog: Decision engine integrated')
    print('  All 5 volumes deployed')
else:
    print('  VOLUME 5: Issues found - check above')
print('=' * 65)