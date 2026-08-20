content = open('packages/integrity/failure_injection.py').read()

# Fix: account_name must MATCH account_id
old = '''    # Check account consistency
    if identity.get("account_id") != identity.get("MT5_login"):
        return False, "BLOCK", "account_id != MT5_login"
    
    if identity.get("account_name") not in ("Live_Micro", "Demo2"):
        return False, "BLOCK", "Invalid account_name"'''

new = '''    # Check account consistency
    if identity.get("account_id") != identity.get("MT5_login"):
        return False, "BLOCK", "account_id != MT5_login"
    
    # account_name must MATCH account_id
    account_mapping = {
        REDACTED_LIVE_ACCOUNT: "Live_Micro",
        REDACTED_DEMO_ACCOUNT: "Demo2",
    }
    expected_name = account_mapping.get(identity.get("account_id"))
    if identity.get("account_name") != expected_name:
        return False, "BLOCK", f"account_name {identity.get('account_name')} != expected {expected_name} for account_id {identity.get('account_id')}"'''

content = content.replace(old, new)
open('packages/integrity/failure_injection.py', 'w').write(content)
print('Fixed: account_name must match account_id')
