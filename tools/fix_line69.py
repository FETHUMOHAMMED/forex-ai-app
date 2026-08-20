lines = open('tests/test_reconciliation.py').readlines()
new_lines = []
for i, line in enumerate(lines):
    # Fix line 69: "class TestErrorCategories:, MT5ConnectionError"
    if 'class TestErrorCategories:' in line and 'MT5ConnectionError' in line:
        new_lines.append('class TestErrorCategories:\n')
        print(f'Fixed line {i+1}: removed leftover import')
        continue
    # Skip the old class-level import line if it exists separately
    if 'from packages.domain.errors import MissingRegimeError, MT5ConnectionError' in line and i > 60:
        continue
    new_lines.append(line)

open('tests/test_reconciliation.py', 'w').writelines(new_lines)
print('Done')
