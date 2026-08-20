"""Verify MT5 Gate has ALL 25 advisor-required items"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import packages.integrity.mt5.deep_health
import packages.integrity.mt5.remaining_checks
from packages.integrity.registry import registry

# The 25 advisor-required MT5 items
advisor_items = [
    # Connectivity
    ("MT5-001", "Terminal connected", "connected"),
    ("MT5-002", "Terminal initialized", "initialized"),
    ("MT5-003", "Account authenticated", "authenticated"),
    ("MT5-004", "Expected account ID", "account_id"),
    ("MT5-005", "Expected environment", "environment"),
    ("MT5-006", "Trading allowed", "trading_allowed"),
    # Symbol
    ("MT5-007", "Symbol available", "symbol_available"),
    ("MT5-008", "Symbol trade mode", "trade_mode"),
    ("MT5-009", "Market data available", "market_data"),
    ("MT5-010", "Bid available", "bid"),
    ("MT5-011", "Ask available", "ask"),
    ("MT5-012", "Spread acceptable", "spread"),
    # Queries
    ("MT5-013", "Positions query working", "positions_query"),
    ("MT5-014", "Orders query working", "orders_query"),
    ("MT5-015", "Deals query working", "deals_query"),
    # History
    ("MT5-016", "History orders query", "history_orders"),
    ("MT5-017", "History positions query", "history_positions"),
    # Symbol specs
    ("MT5-018", "Volume limits", "volume_limits"),
    ("MT5-019", "Contract size", "contract_size"),
    ("MT5-020", "Tick value", "tick_value"),
    # Account
    ("MT5-021", "Account currency", "currency"),
    ("MT5-022", "Margin info", "margin"),
    # Identity
    ("MT5-023", "Order/Position/Deal distinction", "identity_distinction"),
    ("MT5-024", "Position reconciliation", "position_reconciliation"),
    ("MT5-025", "Position-level deals (not symbol-wide)", "position_deals"),
]

# Collect all MT5 checks
mt5_checks = {}
for fn in registry.get_all():
    result = fn()
    if result.domain == 'mt5':
        mt5_checks[result.check] = result

print("=" * 70)
print("  MT5 GATE - 25 ITEM ADVISOR VERIFICATION")
print("=" * 70)

present = 0
passing = 0
for item_id, description, check_name in advisor_items:
    if check_name in mt5_checks:
        present += 1
        result = mt5_checks[check_name]
        icon = "PASS" if result.passed else "FAIL"
        if result.passed:
            passing += 1
        print(f"  [{icon}] {item_id}: {description}")
        print(f"       Check: {check_name} -> {result.detail}")
    else:
        print(f"  [MISSING] {item_id}: {description}")
        print(f"       Check: {check_name} NOT REGISTERED")
    print()

print(f"  {'='*55}")
print(f"  ITEMS PRESENT: {present}/25")
print(f"  ITEMS PASSING: {passing}/25")

if present == 25 and passing == 25:
    print(f"\n  VERDICT: MT5 GATE COMPLETE - ALL 25 ADVISOR ITEMS PRESENT AND PASSING")
elif present == 25:
    print(f"\n  VERDICT: ALL 25 ITEMS PRESENT ({passing} passing)")
else:
    missing = 25 - present
    print(f"\n  VERDICT: INCOMPLETE - {missing} ITEMS MISSING")
print("=" * 70)
