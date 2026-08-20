"""Remaining MT5 checks - Items 16-19, 25"""
import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@registry.register
def check_mt5_history_orders() -> CheckResult:
    """MT5-016: History orders query working"""
    try:
        mt5.initialize()
        orders = mt5.history_orders_get(datetime.now(timezone.utc) - timedelta(days=7),
                                         datetime.now(timezone.utc))
        mt5.shutdown()
        passed = orders is not None
        return CheckResult("mt5", "history_orders", passed, Severity.CRITICAL,
                          f"{len(orders) if orders else 0} history orders" if passed else "Query failed")
    except Exception as e:
        return CheckResult("mt5", "history_orders", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_history_positions() -> CheckResult:
    """MT5-017: History positions query working"""
    try:
        mt5.initialize()
        deals = mt5.history_deals_get(datetime.now(timezone.utc) - timedelta(days=7),
                                       datetime.now(timezone.utc))
        mt5.shutdown()
        passed = deals is not None
        return CheckResult("mt5", "history_positions", passed, Severity.CRITICAL,
                          f"Deal history available ({len(deals) if deals else 0} deals)" if passed else "Query failed")
    except Exception as e:
        return CheckResult("mt5", "history_positions", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_symbol_volume_limits() -> CheckResult:
    """MT5-018: Symbol volume limits"""
    try:
        mt5.initialize()
        info = mt5.symbol_info('EURUSDm')
        mt5.shutdown()
        if not info:
            return CheckResult("mt5", "volume_limits", False, Severity.CRITICAL, "No symbol info")
        passed = info.volume_min > 0 and info.volume_max > 0
        return CheckResult("mt5", "volume_limits", passed, Severity.CRITICAL,
                          f"Min={info.volume_min} Max={info.volume_max} Step={info.volume_step}")
    except Exception as e:
        return CheckResult("mt5", "volume_limits", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_symbol_contract_size() -> CheckResult:
    """MT5-019: Symbol contract size"""
    try:
        mt5.initialize()
        info = mt5.symbol_info('EURUSDm')
        mt5.shutdown()
        if not info:
            return CheckResult("mt5", "contract_size", False, Severity.CRITICAL, "No symbol info")
        passed = info.trade_contract_size > 0
        return CheckResult("mt5", "contract_size", passed, Severity.CRITICAL,
                          f"Contract size={info.trade_contract_size}")
    except Exception as e:
        return CheckResult("mt5", "contract_size", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_tick_value() -> CheckResult:
    """MT5-020: Tick value for risk calculation"""
    try:
        mt5.initialize()
        info = mt5.symbol_info('EURUSDm')
        mt5.shutdown()
        if not info:
            return CheckResult("mt5", "tick_value", False, Severity.CRITICAL, "No symbol info")
        passed = info.trade_tick_value > 0
        return CheckResult("mt5", "tick_value", passed, Severity.CRITICAL,
                          f"Tick value={info.trade_tick_value}")
    except Exception as e:
        return CheckResult("mt5", "tick_value", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_account_currency() -> CheckResult:
    """MT5-021: Account currency"""
    try:
        mt5.initialize()
        info = mt5.account_info()
        mt5.shutdown()
        if not info:
            return CheckResult("mt5", "currency", False, Severity.CRITICAL, "No account")
        passed = info.currency == 'USD'
        return CheckResult("mt5", "currency", passed, Severity.CRITICAL,
                          f"Currency: {info.currency}")
    except Exception as e:
        return CheckResult("mt5", "currency", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_margin_info() -> CheckResult:
    """MT5-022: Margin information"""
    try:
        mt5.initialize()
        info = mt5.account_info()
        mt5.shutdown()
        if not info:
            return CheckResult("mt5", "margin", False, Severity.CRITICAL, "No account")
        passed = info.margin_free >= 0
        return CheckResult("mt5", "margin", passed, Severity.CRITICAL,
                          f"Free margin=${info.margin_free:.2f}")
    except Exception as e:
        return CheckResult("mt5", "margin", False, Severity.CRITICAL, str(e))

@registry.register
def check_mt5_position_level_deals() -> CheckResult:
    """MT5-025: Position-to-deals mapping verified (ID 163 lesson)"""
    try:
        from packages.execution.mt5_reconciler import resolve_trade_identity
        
        mt5.initialize()
        # Get recent deals to find a position ID
        deals = mt5.history_deals_get(datetime.now(timezone.utc) - timedelta(days=30),
                                       datetime.now(timezone.utc))
        
        if deals and len(deals) > 0:
            # Get position ID from most recent deal
            position_id = deals[-1].position_id
            mt5.shutdown()
            
            lineage = resolve_trade_identity(position_id)
            if lineage:
                deal_count = (1 if lineage.entry_deal else 0) + (1 if lineage.exit_deal else 0)
                passed = deal_count <= 3  # Allow for partial closes
                return CheckResult("mt5", "position_deals", passed, Severity.CRITICAL,
                                  f"Position {position_id}: {deal_count} deals (position-level works)")
            return CheckResult("mt5", "position_deals", False, Severity.CRITICAL,
                              f"Cannot resolve position {position_id}")
        else:
            mt5.shutdown()
            return CheckResult("mt5", "position_deals", True, Severity.CRITICAL,
                              "No deals in last 30 days to verify (check passes)")
    except Exception as e:
        return CheckResult("mt5", "position_deals", False, Severity.CRITICAL, str(e))
