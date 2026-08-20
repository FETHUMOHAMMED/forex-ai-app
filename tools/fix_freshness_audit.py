"""Fix freshness check for HISTORICAL trades - use signal time vs execution time."""
content = open('tools/qualified_trade_check.py').read()

old = '''    # 1. FRESH SIGNAL
    signal_age_ms = t.get('signal_age_ms')
    checks['fresh_signal'] = signal_age_ms is not None and signal_age_ms < 120000'''

new = '''    # 1. FRESH SIGNAL (historical audit: compare signal time vs execution time)
    signal_age_ms = t.get('signal_age_ms')
    
    if signal_age_ms is not None:
        # New code: signal_age_ms is stored directly
        checks['fresh_signal'] = signal_age_ms < 120000
    else:
        # Historical trade: calculate from timestamps if available
        signal_ts = t.get('signal_timestamp') or t.get('planned_entry_time')
        execution_ts = t.get('timestamp')  # This is the DB entry time = execution time
        
        if signal_ts and execution_ts:
            from datetime import datetime as dt
            try:
                signal_time = dt.fromisoformat(str(signal_ts).replace('Z', '+00:00'))
                exec_time = dt.fromisoformat(str(execution_ts).replace('Z', '+00:00'))
                age_seconds = (exec_time - signal_time).total_seconds()
                checks['fresh_signal'] = age_seconds < 120
            except:
                checks['fresh_signal'] = False
        else:
            # Cannot determine freshness = fail closed
            checks['fresh_signal'] = False'''

content = content.replace(old, new)
open('tools/qualified_trade_check.py', 'w').write(content)
print('Fixed: historical freshness uses signal_time vs execution_time')
