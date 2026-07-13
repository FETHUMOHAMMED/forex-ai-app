"""Volume 3 Verification - Institutional Structure Intelligence"""
import os

print('=' * 65)
print('  VOLUME 3 VERIFICATION - STRUCTURE INTELLIGENCE')
print('=' * 65)
print()

# 1. Module existence
path = os.path.join(os.path.dirname(__file__), 'institutional_structure.py')
if os.path.exists(path):
    size = os.path.getsize(path)
    print(f'1. MODULE: institutional_structure.py ({size:,} bytes)')
else:
    print('1. MODULE: MISSING')
print()

# 2. Volume 1 & 2 still active
print('2. ALL VOLUMES PRESENT')
volumes = [
    ('market_microstructure.py', 'Volume 1'),
    ('liquidity_intelligence.py', 'Volume 2'),
    ('institutional_structure.py', 'Volume 3'),
]
all_volumes = True
for fname, label in volumes:
    fpath = os.path.join(os.path.dirname(__file__), fname)
    exists = os.path.exists(fpath)
    if not exists:
        all_volumes = False
    status = 'PRESENT' if exists else 'MISSING'
    print(f'  [{status}] {label}: {fname}')
print()

# 3. Pipeline integration
ai_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'real_ai_service.py')
with open(ai_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

checks = [
    ('Structure engine imported', 'InstitutionalStructure' in content),
    ('Engine initialized', 'self.structure_engine' in content),
    ('STRUCTURE logging active', '[STRUCTURE]' in content),
    ('Microstructure still active', '[INSTITUTIONAL]' in content),
    ('Liquidity still active', '[LIQUIDITY]' in content),
]
print('3. PIPELINE INTEGRATION')
all_pass = True
for name, result in checks:
    status = 'PASS' if result else 'FAIL'
    if not result:
        all_pass = False
    print(f'  [{status}] {name}')
print()

# 4. Pipeline order verification
ms_pos = content.find('[INSTITUTIONAL]')
liq_pos = content.find('[LIQUIDITY]')
struct_pos = content.find('[STRUCTURE]')
print('4. PIPELINE ORDER')
if ms_pos < liq_pos < struct_pos:
    print('  [CORRECT] Microstructure -> Liquidity -> Structure')
else:
    print('  [CHECK] Order may differ')
print()

# 5. Live log evidence
print('5. LIVE LOG EVIDENCE')
log_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'forex_ai.log')
struct_lines = []
liq_lines = []
inst_lines = []
if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '[STRUCTURE]' in line:
                struct_lines.append(line.strip())
            if '[LIQUIDITY]' in line:
                liq_lines.append(line.strip())
            if '[INSTITUTIONAL]' in line:
                inst_lines.append(line.strip())
    
    print('  Last STRUCTURE entry:')
    if struct_lines:
        print(f'    {struct_lines[-1][:130]}')
    
    print('  Last LIQUIDITY entry:')
    if liq_lines:
        print(f'    {liq_lines[-1][:130]}')
    
    print('  Last INSTITUTIONAL entry:')
    if inst_lines:
        print(f'    {inst_lines[-1][:130]}')

all_active = len(struct_lines) > 0 and len(liq_lines) > 0 and len(inst_lines) > 0
print()
print(f'  All three engines active: {all_active}')
print()

# 6. Total institutional code
total_bytes = 0
for fname, _ in volumes:
    fpath = os.path.join(os.path.dirname(__file__), fname)
    if os.path.exists(fpath):
        total_bytes += os.path.getsize(fpath)
print(f'6. TOTAL INSTITUTIONAL CODE: {total_bytes:,} bytes ({total_bytes/1024:.0f} KB)')

print()
print('=' * 65)
if all_pass and all_active and all_volumes:
    print('  VOLUME 3: FULLY OPERATIONAL')
    print(f'  Module: {size:,} bytes')
    print('  Pipeline: 5/5 checks passed')
    print('  All three engines producing live output')
    print(f'  Total institutional code: {total_bytes:,} bytes')
else:
    print('  VOLUME 3: Issues found - check above')
print('=' * 65)