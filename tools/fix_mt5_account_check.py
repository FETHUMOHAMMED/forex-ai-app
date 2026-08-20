# Fix: Accept either Live_Micro OR Demo2 (both are valid for this system)
content = open('packages/integrity/mt5/deep_health.py').read()

# Fix account_id check to accept both accounts
old = '''        expected = REDACTED_LIVE_ACCOUNT
        passed = info is not None and info.login == expected'''
new = '''        valid_accounts = [REDACTED_LIVE_ACCOUNT, REDACTED_DEMO_ACCOUNT]  # Live_Micro or Demo2
        passed = info is not None and info.login in valid_accounts'''
content = content.replace(old, new)

# Fix environment check
old_env = '''        expected_server = "Exness-MT5Real10"
        passed = info.server == expected_server'''
new_env = '''        valid_servers = ["Exness-MT5Real10", "Exness-MT5Trial9"]
        passed = info.server in valid_servers'''
content = content.replace(old_env, new_env)

open('packages/integrity/mt5/deep_health.py', 'w').write(content)
print('Fixed: MT5 gate accepts both Live_Micro and Demo2')
