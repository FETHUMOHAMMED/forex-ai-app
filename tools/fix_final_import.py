"""Fix MissingRegimeError and MT5ConnectionError imports at module level"""
path = 'tests/test_reconciliation.py'
content = open(path).read()

# Update the module-level import to include the missing names
old_import = """from packages.domain.errors import (
    PhantomTradeError, OrphanPositionError, PnLMismatchError, TimestampError
)"""

new_import = """from packages.domain.errors import (
    PhantomTradeError, OrphanPositionError, PnLMismatchError, TimestampError,
    MissingRegimeError, MT5ConnectionError
)"""

content = content.replace(old_import, new_import)

# Remove the class-level import
content = content.replace(
    'class TestErrorCategories:\n    from packages.domain.errors import MissingRegimeError, MT5ConnectionError',
    'class TestErrorCategories:'
)

open(path, 'w').write(content)
print('FIXED: Added MissingRegimeError and MT5ConnectionError to module-level imports')
