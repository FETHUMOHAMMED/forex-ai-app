import sys
sys.path.insert(0, '.')
from packages.execution.resilience import resilience, FailureMode

tests = [
    ("MT5 disconnect", resilience.handle_mt5_disconnect("Live_Micro", max_retries=1)),
    ("Partial fill", resilience.handle_order_partial_fill(0.05, 0.01)),
    ("Slippage", resilience.handle_price_slippage(1.15542, 1.15600)),
    ("Duplicate signal", resilience.handle_duplicate_signal("EURUSD", "SELL", 589584400)),
    ("Broker reject", resilience.handle_broker_reject(10016, "Invalid stops")),
    ("Market gap", resilience.handle_market_gap("EURUSD", 15.0)),
    ("Missing metadata", resilience.handle_missing_metadata("regime", "EURUSD")),
    ("Stale signal", resilience.handle_stale_signal("EURUSD", 600)),
    ("Wrong account", resilience.handle_wrong_account(REDACTED_LIVE_ACCOUNT, REDACTED_DEMO_ACCOUNT)),
]
for name, result in tests:
    icon = "[OK]" if result.handled else "[REJECT]"
    print(f"{icon} {name}: {result.action_taken[:80]}")

status = resilience.get_status()
print(f"\nTotal failures handled: {status['total_failures']}")
