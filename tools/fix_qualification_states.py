"""Fix: Add UNVERIFIED state for historical trades missing telemetry."""
content = open('tools/qualified_trade_check.py').read()

# Add UNVERIFIED status for missing telemetry
old = '''    # 8. VALID SPREAD
    spread = t.get('spread_at_execution')
    checks['valid_spread'] = spread is not None and spread <= 0.0015
    
    # 9. VALID RISK
    risk_budget = t.get('risk_budget_usd')
    actual_risk = t.get('actual_risk_usd')
    if risk_budget and actual_risk:
        checks['valid_risk'] = actual_risk <= risk_budget * 1.01
    else:
        checks['valid_risk'] = False'''

new = '''    # 8. VALID SPREAD (UNVERIFIED if no telemetry)
    spread = t.get('spread_at_execution')
    if spread is not None:
        checks['valid_spread'] = spread <= 0.0015
    else:
        checks['valid_spread'] = None  # UNVERIFIED - no historical telemetry
    
    # 9. VALID RISK (UNVERIFIED if no telemetry)
    risk_budget = t.get('risk_budget_usd')
    actual_risk = t.get('actual_risk_usd')
    if risk_budget is not None and actual_risk is not None:
        checks['valid_risk'] = actual_risk <= risk_budget * 1.01
    else:
        checks['valid_risk'] = None  # UNVERIFIED - no risk snapshot'''

content = content.replace(old, new)

# Also update fresh_signal to use UNVERIFIED
old_fresh = '''        else:
            # Cannot determine freshness = fail closed
            checks['fresh_signal'] = False'''

new_fresh = '''        else:
            # Cannot determine freshness = UNVERIFIED (not FAIL)
            checks['fresh_signal'] = None'''

content = content.replace(old_fresh, new_fresh)

# Update the print to show UNVERIFIED
old_print = '''    for check, passed in result.get("checks", {}).items():
        icon = "PASS" if passed else "FAIL"
        print(f"    [{icon}] {check}")'''

new_print = '''    for check, passed in result.get("checks", {}).items():
        if passed is True:
            icon = "PASS"
        elif passed is False:
            icon = "FAIL"
        else:
            icon = "UNVERIFIED"
        print(f"    [{icon}] {check}")'''

content = content.replace(old_print, new_print)

# Update failed_checks to only include actual False (not None)
old_failed = '''    all_pass = all(checks.values())
    failed = [k for k, v in checks.items() if not v]'''

new_failed = '''    # Only count actual FAILs (not UNVERIFIED)
    failed = [k for k, v in checks.items() if v is False]
    unverified = [k for k, v in checks.items() if v is None]
    all_pass = len(failed) == 0 and len(unverified) == 0'''

content = content.replace(old_failed, new_failed)

# Update result to include unverified
old_result = '''    return {
        "qualified": all_pass,
        "checks": checks,
        "failed_checks": failed,
        "trade_id": trade_id,
    }'''

new_result = '''    return {
        "qualified": all_pass,
        "checks": checks,
        "failed_checks": failed,
        "unverified_checks": unverified,
        "trade_id": trade_id,
    }'''

content = content.replace(old_result, new_result)

open('tools/qualified_trade_check.py', 'w').write(content)
print('Fixed: UNVERIFIED state for missing historical telemetry')
