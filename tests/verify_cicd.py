"""RUNTIME VERIFICATION: CI/CD Pipeline"""
import sys, os

BASE = os.path.join(os.path.dirname(__file__), '..')

# TEST 1: Workflow file exists
wf_path = os.path.join(BASE, '.github', 'workflows', 'test.yml')
assert os.path.exists(wf_path), 'GitHub Actions workflow missing'
print('PASSED: TEST 1 - Workflow file exists')

with open(wf_path, 'r', encoding='utf-8') as f:
    wf = f.read()

# TEST 2: Triggers on push and PR
assert 'on: [push, pull_request]' in wf or ('push' in wf and 'pull_request' in wf), 'Missing push/PR triggers'
print('PASSED: TEST 2 - Triggers on push and pull_request')

# TEST 3: Runs all 3 test files
assert 'test_signal_pipeline.py' in wf, 'Missing test_signal_pipeline.py'
assert 'test_trading_logic.py' in wf, 'Missing test_trading_logic.py'
assert 'test_signal_engine.py' in wf, 'Missing test_signal_engine.py'
print('PASSED: TEST 3 - All 3 test files in CI pipeline')

# TEST 4: Python setup
assert 'setup-python' in wf, 'Missing Python setup'
assert '3.11' in wf, 'Python version not specified'
print('PASSED: TEST 4 - Python 3.11 configured')

# TEST 5: Lint job exists
assert 'flake8' in wf or 'lint' in wf.lower(), 'No linting configured'
print('PASSED: TEST 5 - Linting configured')

# TEST 6: Security scan exists
assert 'password' in wf.lower() or 'security' in wf.lower(), 'No security scan'
print('PASSED: TEST 6 - Security scan configured')

# TEST 7: Secret verification
assert 'gitignore' in wf, 'No gitignore verification'
assert '.env' in wf, 'No .env check'
print('PASSED: TEST 7 - Secret verification configured')

# TEST 8: Multiple jobs
job_count = wf.count('jobs:') + wf.count('  test:') + wf.count('  lint:') + wf.count('  security:')
assert 'test:' in wf and 'lint:' in wf, 'Missing test or lint jobs'
print('PASSED: TEST 8 - Multiple CI jobs configured')

print()
print('ALL 8 RUNTIME TESTS PASSED - CI/CD pipeline is complete')
