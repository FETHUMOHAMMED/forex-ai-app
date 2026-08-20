"""Add detailed risk calculation and timestamp sources to evidence."""
content = open('packages/execution/trade_evidence.py').read()

# Add risk calculation breakdown to the print
old = '''        print(f"\\n  RISK:")
        print(f"    Equity: ${self.equity:.2f}")
        print(f"    Budget: ${self.risk_budget:.4f}")
        print(f"    Actual: ${self.actual_risk or 'N/A'}")
        print(f"    Volume: {self.volume}")'''

new = '''        print(f"\\n  RISK:")
        print(f"    Equity: ${self.equity:.2f}")
        print(f"    Budget: ${self.risk_budget:.4f}")
        print(f"    Actual: ${self.actual_risk or 'N/A'}")
        print(f"    Volume: {self.volume}")
        
        # Detailed risk calculation (auditor can verify)
        if self.planned_entry and self.planned_sl:
            sl_distance = abs(self.planned_entry - self.planned_sl)
            sl_pips = sl_distance / 0.0001
            pip_value = self.volume * 10.0  # $10/pip for 1 lot, $0.10 for 0.01
            gross_risk = sl_pips * pip_value
            print(f"\\n  RISK CALCULATION (Auditable):")
            print(f"    Entry:          {self.planned_entry}")
            print(f"    Stop:           {self.planned_sl}")
            print(f"    Distance:       {sl_pips:.1f} pips")
            print(f"    Volume:         {self.volume}")
            print(f"    Pip value:      ${pip_value:.2f}")
            print(f"    Gross risk:     ${gross_risk:.2f}")'''

content = content.replace(old, new)

# Add timestamp source fields
old_dataclass = '''    # Timestamps
    signal_time: str
    execution_attempt_time: str
    mt5_open_time: Optional[str] = None
    mt5_close_time: Optional[str] = None'''

new_dataclass = '''    # Timestamps (with sources)
    signal_time: str
    signal_time_source: str = "APP"  # APP or MT5
    execution_attempt_time: str
    execution_time_source: str = "APP"
    mt5_open_time: Optional[str] = None
    mt5_open_time_source: str = "MT5"
    mt5_close_time: Optional[str] = None
    mt5_close_time_source: str = "MT5"'''

content = content.replace(old_dataclass, new_dataclass)

open('packages/execution/trade_evidence.py', 'w').write(content)
print('Added detailed risk calculation + timestamp sources')
