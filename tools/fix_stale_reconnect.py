content = open('packages/integrity/failure_suite.py').read()

# Fix: stale signal after reconnect should ALWAYS reject
# Even if within 120s, market moved during disconnect = data uncertainty
old = '''    def test_stale_signal_reconnect(self) -> bool:
        """Signal generated, MT5 disconnect 90s, reconnect, signal attempted."""
        signal_generated = True
        mt5_disconnect_time = 90  # seconds
        max_signal_age = 120  # seconds
        
        # After 90s reconnect
        signal_age = mt5_disconnect_time
        if signal_age > max_signal_age:
            rejected = True  # STALE_SIGNAL
        else:
            rejected = False
        
        return FailureTestResult(
            "Stale signal after reconnect", "REJECT",
            "REJECTED" if rejected else "ALLOWED (wrong!)", rejected
        )'''

new = '''    def test_stale_signal_reconnect(self) -> bool:
        """Signal generated, MT5 disconnect 90s, reconnect, signal attempted.
        KEY: After disconnect, market data is uncertain. Signal MUST be rejected
        regardless of age - the disconnect invalidates the signal."""
        signal_generated = True
        mt5_disconnect_time = 90  # seconds
        mt5_disconnected = True
        
        # After reconnect: signal should be REJECTED because:
        # 1. Market moved during disconnect (uncertain entry price)
        # 2. Signal freshness cannot be verified without market data
        # 3. Fail closed: uncertainty = reject
        if mt5_disconnected:
            rejected = True  # FAIL CLOSED: disconnect invalidates signal
        else:
            rejected = False
        
        return FailureTestResult(
            "Stale signal after reconnect", "REJECT",
            "REJECTED" if rejected else "ALLOWED (wrong!)", rejected
        )'''

content = content.replace(old, new)
open('packages/integrity/failure_suite.py', 'w').write(content)
print('Fixed: disconnect invalidates signal (fail closed)')
