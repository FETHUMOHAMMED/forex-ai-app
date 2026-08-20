"""Fix: Checker should CALL canonical reconciler, not rely on stored field."""
content = open('tools/qualified_trade_check.py').read()

old = '''    # 12. RECONCILED
    checks['reconciled'] = (
        t.get('execution_contract_valid') == 1 and
        t.get('pnl') is not None
    )'''

new = '''    # 12. RECONCILED (call canonical reconciler, not stored field)
    if t.get('mt5_position_id') is not None:
        try:
            from packages.execution.mt5_reconciler import resolve_trade_identity
            lineage = resolve_trade_identity(t['mt5_position_id'])
            if lineage and lineage.is_complete:
                # Check PnL matches
                if t.get('pnl') is not None and lineage.net_pnl is not None:
                    checks['reconciled'] = abs(t['pnl'] - lineage.net_pnl) < 0.01
                else:
                    checks['reconciled'] = False
            else:
                checks['reconciled'] = False
        except Exception as e:
            checks['reconciled'] = False
    else:
        checks['reconciled'] = False'''

content = content.replace(old, new)
open('tools/qualified_trade_check.py', 'w').write(content)
print('Fixed: reconciliation check calls canonical reconciler directly')
