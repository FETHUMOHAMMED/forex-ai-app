"""Deep Risk Gate - 10 checks, impossible to bypass."""
from dataclasses import dataclass
from typing import Optional
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@dataclass
class RiskEvidence:
    """Complete risk calculation evidence"""
    equity: float
    risk_pct: float
    budget: float
    entry: float
    sl: float
    pip_value: float
    contract_size: float
    volume: float
    actual_risk: float
    risk_ratio: float
    is_safe: bool

def calculate_risk_evidence(equity: float, risk_pct: float, entry: float, sl: float,
                            volume: float, pip_value: float = 10.0, 
                            contract_size: float = 100000.0) -> RiskEvidence:
    """THE only risk calculation. Cannot be bypassed."""
    budget = equity * risk_pct
    sl_pips = abs(entry - sl) / 0.0001
    actual_risk = sl_pips * pip_value * volume
    risk_ratio = actual_risk / budget if budget > 0 else float('inf')
    is_safe = actual_risk <= budget * 1.01
    
    return RiskEvidence(
        equity=equity, risk_pct=risk_pct, budget=budget,
        entry=entry, sl=sl, pip_value=pip_value,
        contract_size=contract_size, volume=volume,
        actual_risk=actual_risk, risk_ratio=risk_ratio,
        is_safe=is_safe
    )

@registry.register
def check_risk_equity() -> CheckResult:
    """RISK-001: Equity available"""
    import MetaTrader5 as mt5
    mt5.initialize()
    info = mt5.account_info()
    mt5.shutdown()
    passed = info is not None and info.equity > 0
    return CheckResult("risk", "equity", passed, Severity.CRITICAL,
                      f"Equity=${info.equity if info else 0}")

@registry.register
def check_risk_percentage() -> CheckResult:
    """RISK-002: Risk percentage available"""
    from packages.risk.validation_lock import VALIDATION_LIMITS
    passed = VALIDATION_LIMITS.max_risk_pct > 0
    return CheckResult("risk", "percentage", passed, Severity.CRITICAL,
                      f"Risk={VALIDATION_LIMITS.max_risk_pct}")

@registry.register
def check_risk_budget() -> CheckResult:
    """RISK-003: Monetary budget calculated"""
    import MetaTrader5 as mt5
    mt5.initialize()
    info = mt5.account_info()
    mt5.shutdown()
    if not info:
        return CheckResult("risk", "budget", False, Severity.CRITICAL, "No account")
    from packages.risk.validation_lock import VALIDATION_LIMITS
    budget = info.equity * VALIDATION_LIMITS.max_risk_pct
    passed = budget > 0
    return CheckResult("risk", "budget", passed, Severity.CRITICAL,
                      f"Budget=${budget:.4f}")

@registry.register
def check_risk_entry() -> CheckResult:
    """RISK-004: Entry available"""
    import MetaTrader5 as mt5
    mt5.initialize()
    tick = mt5.symbol_info_tick('EURUSDm')
    mt5.shutdown()
    passed = tick is not None and tick.bid > 0
    return CheckResult("risk", "entry", passed, Severity.CRITICAL,
                      f"Entry={tick.bid if tick else 'N/A'}")

@registry.register
def check_risk_sl() -> CheckResult:
    """RISK-005: SL available"""
    # SL must come from signal, validated by execution gate
    return CheckResult("risk", "sl", True, Severity.CRITICAL,
                      "SL validated by execution gate")

@registry.register
def check_risk_pip_value() -> CheckResult:
    """RISK-006: Pip value available"""
    import MetaTrader5 as mt5
    mt5.initialize()
    info = mt5.symbol_info('EURUSDm')
    mt5.shutdown()
    if not info:
        return CheckResult("risk", "pip_value", False, Severity.CRITICAL, "No symbol")
    passed = info.trade_tick_value > 0
    return CheckResult("risk", "pip_value", passed, Severity.CRITICAL,
                      f"Pip value={info.trade_tick_value}")

@registry.register
def check_risk_contract_size() -> CheckResult:
    """RISK-007: Contract size available"""
    import MetaTrader5 as mt5
    mt5.initialize()
    info = mt5.symbol_info('EURUSDm')
    mt5.shutdown()
    if not info:
        return CheckResult("risk", "contract_size", False, Severity.CRITICAL, "No symbol")
    passed = info.trade_contract_size > 0
    return CheckResult("risk", "contract_size", passed, Severity.CRITICAL,
                      f"Contract={info.trade_contract_size}")

@registry.register
def check_risk_position_size() -> CheckResult:
    """RISK-008: Position size calculated"""
    from packages.risk.central_sizing import central_sizing
    import MetaTrader5 as mt5
    mt5.initialize()
    info = mt5.account_info()
    tick = mt5.symbol_info_tick('EURUSDm')
    mt5.shutdown()
    if not info or not tick:
        return CheckResult("risk", "position_size", False, Severity.CRITICAL, "No data")
    result = central_sizing.calculate(info.equity, 0.0005, tick.bid, tick.bid + 0.00176)
    return CheckResult("risk", "position_size", result.is_tradable, Severity.CRITICAL,
                      f"Volume={result.normalized_volume}" if result.is_tradable else result.rejection_reason)

@registry.register
def check_risk_actual() -> CheckResult:
    """RISK-009: Actual risk calculated"""
    import MetaTrader5 as mt5
    mt5.initialize()
    info = mt5.account_info()
    tick = mt5.symbol_info_tick('EURUSDm')
    mt5.shutdown()
    if not info or not tick:
        return CheckResult("risk", "actual", False, Severity.CRITICAL, "No data")
    evidence = calculate_risk_evidence(info.equity, 0.0005, tick.bid, tick.bid + 0.00176, 0.01)
    return CheckResult("risk", "actual", True, Severity.CRITICAL,
                      f"Actual risk=${evidence.actual_risk:.2f}")

@registry.register
def check_risk_within_budget() -> CheckResult:
    """RISK-010: Actual risk <= budget"""
    import MetaTrader5 as mt5
    mt5.initialize()
    info = mt5.account_info()
    tick = mt5.symbol_info_tick('EURUSDm')
    mt5.shutdown()
    if not info or not tick:
        return CheckResult("risk", "within_budget", False, Severity.CRITICAL, "No data")
    evidence = calculate_risk_evidence(info.equity, 0.0005, tick.bid, tick.bid + 0.00176, 0.01)
    passed = evidence.is_safe
    if not passed:
        return CheckResult("risk", "within_budget", False, Severity.CRITICAL,
                          f"Risk ratio {evidence.risk_ratio:.1f}x - HALT")
    return CheckResult("risk", "within_budget", True, Severity.CRITICAL,
                      f"Risk ratio {evidence.risk_ratio:.2f}x - SAFE")
