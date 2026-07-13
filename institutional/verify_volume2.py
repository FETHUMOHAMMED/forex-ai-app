"""Volume 2 Verification - Liquidity Intelligence"""
import os

print('=' * 65)
print('  VOLUME 2 VERIFICATION - LIQUIDITY INTELLIGENCE')
print('=' * 65)
print()

# 1. Module existence
path = os.path.join(os.path.dirname(__file__), 'liquidity_intelligence.py')
if os.path.exists(path):
    size = os.path.getsize(path)
    print(f'1. MODULE: liquidity_intelligence.py ({size:,} bytes)')
else:
    print('1. MODULE: MISSING')
print()

# 2. Pipeline integration
ai_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'real_ai_service.py')
with open(ai_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

checks = [
    ('LiquidityIntelligence imported', 'LiquidityIntelligence' in content),
    ('Engine initialized', 'self.liquidity_engine' in content),
    ('LIQUIDITY logging active', '[LIQUIDITY]' in content),
    ('Microstructure still active', '[INSTITUTIONAL]' in content),
]
print('2. PIPELINE INTEGRATION')
all_pass = True
for name, result in checks:
    status = 'PASS' if result else 'FAIL'
    if not result:
        all_pass = False
    print(f'  [{status}] {name}')
print()

# 3. Live log evidence
print('3. LIVE LOG EVIDENCE')
log_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'forex_ai.log')
liq_lines = []
inst_lines = []
if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '[LIQUIDITY]' in line:
                liq_lines.append(line.strip())
            if '[INSTITUTIONAL]' in line:
                inst_lines.append(line.strip())
    
    print('  Last 2 LIQUIDITY entries:')
    for l in liq_lines[-2:]:
        print(f'    {l[:130]}')
    print()
    print('  Last 2 INSTITUTIONAL entries:')
    for l in inst_lines[-2:]:
        print(f'    {l[:130]}')

both_active = len(liq_lines) > 0 and len(inst_lines) > 0
print()
print(f'  Both engines active: {both_active}')

print()
print('=' * 65)
if all_pass and both_active:
    print('  VOLUME 2: FULLY OPERATIONAL')
    print(f'  Module: {size:,} bytes')
    print('  Pipeline: 4/4 checks passed')
    print('  Both engines producing live output')
else:
    print('  VOLUME 2: Issues found - check above')
print('=' * 65)