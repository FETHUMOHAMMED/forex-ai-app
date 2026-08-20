"""Fix missing import in test_reconciliation.py"""
path = 'tests/test_reconciliation.py'
content = open(path).read()

# Add import at top of file
if 'from packages.domain.errors import MissingRegimeError' not in content:
    content = content.replace(
        'import pytest',
        'import pytest\nfrom packages.domain.errors import MissingRegimeError'
    )
    open(path, 'w').write(content)
    print('FIXED: Added MissingRegimeError import')
else:
    print('Import already present')
