content = open('packages/execution/trade_evidence.py').read()

# Fix: default fields must come AFTER non-default fields
old = '''    # Timestamps (with sources)
    signal_time: str
    signal_time_source: str = "APP"  # APP or MT5
    execution_attempt_time: str
    execution_time_source: str = "APP"
    mt5_open_time: Optional[str] = None
    mt5_open_time_source: str = "MT5"
    mt5_close_time: Optional[str] = None
    mt5_close_time_source: str = "MT5"'''

new = '''    # Timestamps (with sources)
    signal_time: str
    execution_attempt_time: str
    signal_time_source: str = "APP"  # APP or MT5
    execution_time_source: str = "APP"
    mt5_open_time: Optional[str] = None
    mt5_open_time_source: str = "MT5"
    mt5_close_time: Optional[str] = None
    mt5_close_time_source: str = "MT5"'''

content = content.replace(old, new)
open('packages/execution/trade_evidence.py', 'w').write(content)
print('Fixed dataclass field order')
