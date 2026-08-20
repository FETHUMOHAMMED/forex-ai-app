# Fix position_deals check to work with whichever account is connected
content = open('packages/integrity/mt5/remaining_checks.py').read()

old = '''        from packages.execution.mt5_reconciler import resolve_trade_identity
        # Verify: position 589584400 (ID 163) should return ONLY its own deals
        lineage = resolve_trade_identity(589584400)'''

new = '''        from packages.execution.mt5_reconciler import resolve_trade_identity
        # Get any available position from MT5 history
        deals = mt5.history_deals_get(datetime.now(timezone.utc) - timedelta(days=30),
                                       datetime.now(timezone.utc))
        if deals and len(deals) > 0:
            # Use the most recent position ID
            position_id = deals[-1].position_id
            lineage = resolve_trade_identity(position_id)
        else:
            return CheckResult("mt5", "position_deals", False, Severity.CRITICAL,
                              "No deals in history to verify position-level reconciliation")'''

content = content.replace(old, new)
open('packages/integrity/mt5/remaining_checks.py', 'w').write(content)
print('Fixed position_deals check to use available position')
