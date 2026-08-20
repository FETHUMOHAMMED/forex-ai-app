"""Fix syntax error in broker_exness.py"""
import shutil

# Read the file
with open('ai-service/broker_exness.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The problem is clear from the output:
# Lines 166-174: the if/else block from the previous fix left broken code
# We need to remove lines 166-174 and replace with proper code

# Fix: Remove the broken "if not is_exchange" block entirely
# Lines 165-174 are the broken part (0-indexed: 164-173)
# We'll remove them and just have the request dict without SL/TP

new_lines = []
for i, line in enumerate(lines):
    # Skip the broken block (lines 165-174, 0-indexed 164-173)
    if 164 <= i <= 173:
        continue
    # Also remove the trade_mode/is_exchange lines added earlier
    if 'trade_mode = symbol_info.trade_mode' in line:
        continue
    if 'is_exchange = (trade_mode == 4)' in line:
        continue
    if '# For exchange-mode symbols' in line:
        continue
    if '# Only include SL/TP for non-exchange mode symbols' in line:
        continue
    new_lines.append(line)

# Backup
shutil.copy2('ai-service/broker_exness.py', 'ai-service/broker_exness.py.bak3')

# Write fixed file
with open('ai-service/broker_exness.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed syntax error")
print("Try: python -c \"compile(open('ai-service/broker_exness.py').read(), 'test', 'exec'); print('OK')\"")
