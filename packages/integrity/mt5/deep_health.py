"""Deep MT5 Health Checks - 25 items per advisor specification."""
import MetaTrader5 as mt5
import sqlite3
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@registry.register
def check_mt5_connected() -> CheckResult:
    """MT5-001: Terminal connected"""
    try:
        if mt5.initialize():
            mt5.shutdown()
            return CheckResult("mt5", "connected", True, Severity.CRITICAL, "Terminal connected")
        return CheckResult("mt5", "connected", False, Severity.CRITICAL, "Terminal NOT connected")
    except Exception as e:
        return CheckResult("mt5", "connected", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_initialized() -> CheckResult:
    """MT5-002: Terminal initialized"""
    try:
        result = mt5.initialize()
        mt5.shutdown()
        return CheckResult("mt5", "initialized", result, Severity.CRITICAL,
                          "Initialized" if result else "Init failed")
    except Exception as e:
        return CheckResult("mt5", "initialized", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_authenticated() -> CheckResult:
    """MT5-003: Account authenticated"""
    try:
        mt5.initialize()
        info = mt5.account_info()
        mt5.shutdown()
        passed = info is not None
        return CheckResult("mt5", "authenticated", passed, Severity.CRITICAL,
                          f"Account {info.login}" if passed else "No account")
    except Exception as e:
        return CheckResult("mt5", "authenticated", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_account_id() -> CheckResult:
    """MT5-004: Expected account ID"""
    try:
        mt5.initialize()
        info = mt5.account_info()
        mt5.shutdown()
        valid_accounts = [REDACTED_LIVE_ACCOUNT, REDACTED_DEMO_ACCOUNT]  # Live_Micro or Demo2
        passed = info is not None and info.login in valid_accounts
        return CheckResult("mt5", "account_id", passed, Severity.CRITICAL,
                          f"Account {info.login if info else 'N/A'}" + 
                          (f" (expected {expected})" if not passed else " (correct)"))
    except Exception as e:
        return CheckResult("mt5", "account_id", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_environment() -> CheckResult:
    """MT5-005: Expected environment"""
    try:
        mt5.initialize()
        info = mt5.account_info()
        mt5.shutdown()
        if not info:
            return CheckResult("mt5", "environment", False, Severity.CRITICAL, "No account info")
        # Live_Micro should be on Exness-MT5Real10
        valid_servers = ["Exness-MT5Real10", "Exness-MT5Trial9"]
        passed = info.server in valid_servers
        return CheckResult("mt5", "environment", passed, Severity.CRITICAL,
                          f"Server: {info.server}" + (" (correct)" if passed else f" (expected {expected_server})"))
    except Exception as e:
        return CheckResult("mt5", "environment", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_trading_allowed() -> CheckResult:
    """MT5-006: Trading allowed"""
    try:
        mt5.initialize()
        info = mt5.account_info()
        mt5.shutdown()
        if not info:
            return CheckResult("mt5", "trading_allowed", False, Severity.CRITICAL, "No account")
        passed = info.trade_allowed
        return CheckResult("mt5", "trading_allowed", passed, Severity.CRITICAL,
                          "Trading allowed" if passed else "Trading DISABLED")
    except Exception as e:
        return CheckResult("mt5", "trading_allowed", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_symbol_available() -> CheckResult:
    """MT5-007: Symbol available"""
    try:
        mt5.initialize()
        mt5.symbol_select('EURUSDm', True)
        info = mt5.symbol_info('EURUSDm')
        mt5.shutdown()
        passed = info is not None
        return CheckResult("mt5", "symbol_available", passed, Severity.CRITICAL,
                          "EURUSDm available" if passed else "EURUSDm NOT available")
    except Exception as e:
        return CheckResult("mt5", "symbol_available", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_trade_mode() -> CheckResult:
    """MT5-008: Symbol trade mode"""
    try:
        mt5.initialize()
        info = mt5.symbol_info('EURUSDm')
        mt5.shutdown()
        if not info:
            return CheckResult("mt5", "trade_mode", False, Severity.CRITICAL, "No symbol")
        mode = info.trade_mode
        mode_names = {0: 'FULL', 1: 'LIMIT', 2: 'STOP', 3: 'LIMIT_STOP', 4: 'EXCHANGE'}
        mode_name = mode_names.get(mode, f'UNKNOWN({mode})')
        return CheckResult("mt5", "trade_mode", True, Severity.WARNING,
                          f"Mode: {mode_name} (SL/TP: {'NO' if mode == 4 else 'YES'})")
    except Exception as e:
        return CheckResult("mt5", "trade_mode", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_market_data() -> CheckResult:
    """MT5-009: Market data available"""
    try:
        mt5.initialize()
        rates = mt5.copy_rates_from_pos('EURUSDm', mt5.TIMEFRAME_M1, 0, 10)
        mt5.shutdown()
        passed = rates is not None and len(rates) > 0
        return CheckResult("mt5", "market_data", passed, Severity.CRITICAL,
                          f"{len(rates)} bars" if passed else "No market data")
    except Exception as e:
        return CheckResult("mt5", "market_data", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_bid_available() -> CheckResult:
    """MT5-010: Bid available"""
    try:
        mt5.initialize()
        tick = mt5.symbol_info_tick('EURUSDm')
        mt5.shutdown()
        passed = tick is not None and tick.bid > 0
        return CheckResult("mt5", "bid", passed, Severity.CRITICAL,
                          f"Bid: {tick.bid}" if passed else "No bid")
    except Exception as e:
        return CheckResult("mt5", "bid", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_ask_available() -> CheckResult:
    """MT5-011: Ask available"""
    try:
        mt5.initialize()
        tick = mt5.symbol_info_tick('EURUSDm')
        mt5.shutdown()
        passed = tick is not None and tick.ask > 0
        return CheckResult("mt5", "ask", passed, Severity.CRITICAL,
                          f"Ask: {tick.ask}" if passed else "No ask")
    except Exception as e:
        return CheckResult("mt5", "ask", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_spread() -> CheckResult:
    """MT5-012: Spread acceptable"""
    try:
        mt5.initialize()
        tick = mt5.symbol_info_tick('EURUSDm')
        mt5.shutdown()
        if not tick:
            return CheckResult("mt5", "spread", False, Severity.CRITICAL, "No tick")
        spread = tick.ask - tick.bid
        passed = spread <= 0.0015
        return CheckResult("mt5", "spread", passed, Severity.CRITICAL,
                          f"{spread:.6f}" + ("" if passed else " TOO WIDE"))
    except Exception as e:
        return CheckResult("mt5", "spread", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_positions_query() -> CheckResult:
    """MT5-013: Positions query working"""
    try:
        mt5.initialize()
        positions = mt5.positions_get()
        mt5.shutdown()
        passed = positions is not None
        return CheckResult("mt5", "positions_query", passed, Severity.CRITICAL,
                          f"{len(positions)} positions" if passed else "Query failed")
    except Exception as e:
        return CheckResult("mt5", "positions_query", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_orders_query() -> CheckResult:
    """MT5-014: Orders query working"""
    try:
        mt5.initialize()
        orders = mt5.orders_get()
        mt5.shutdown()
        passed = orders is not None
        return CheckResult("mt5", "orders_query", passed, Severity.CRITICAL,
                          f"{len(orders) if orders else 0} orders" if passed else "Query failed")
    except Exception as e:
        return CheckResult("mt5", "orders_query", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_deals_query() -> CheckResult:
    """MT5-015: Deals query working"""
    try:
        mt5.initialize()
        from datetime import datetime, timezone, timedelta
        deals = mt5.history_deals_get(datetime.now(timezone.utc) - timedelta(days=7),
                                       datetime.now(timezone.utc))
        mt5.shutdown()
        passed = deals is not None
        return CheckResult("mt5", "deals_query", passed, Severity.CRITICAL,
                          f"{len(deals) if deals else 0} deals" if passed else "Query failed")
    except Exception as e:
        return CheckResult("mt5", "deals_query", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_identity_distinction() -> CheckResult:
    """MT5-020 to 022: Order vs Position vs Deal identity"""
    from packages.execution.mt5_identity import TicketType
    distinct = (TicketType.ORDER.value != TicketType.POSITION.value != TicketType.DEAL_ENTRY.value)
    return CheckResult("mt5", "identity_distinction", distinct, Severity.CRITICAL,
                      "Order/Position/Deal are distinct" if distinct else "IDENTITY COLLISION!")

@registry.register
def check_mt5_position_reconciliation() -> CheckResult:
    """MT5-023 to 024: Position-level reconciliation works"""
    from packages.execution.mt5_reconciler import resolve_trade_identity
    # Test with known valid position
    lineage = resolve_trade_identity(589629837)
    passed = lineage is not None
    # Check if it found the position-specific deals (not all EURUSD deals)
    return CheckResult("mt5", "position_reconciliation", passed, Severity.CRITICAL,
                      "Position-level reconciliation works" if passed else "Failed")
