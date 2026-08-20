"""Fix the last failing test - MissingRegimeError scope"""
path = 'tests/test_reconciliation.py'
content = open(path).read()

# The class has its own from-import that shadows the module-level one
# Remove the class-level import and use the module-level one
content = content.replace(
    'class TestErrorCategories:\n    from packages.domain.errors import MissingRegimeError',
    'class TestErrorCategories:'
)

open(path, 'w').write(content)
print('FIXED: Removed class-level import that was shadowing')
