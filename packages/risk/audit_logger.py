"""P0: Immutable audit record for EVERY order attempt (including rejected).
Answers: "Why didn't the system trade?" - not just "What did it trade?"
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

AUDIT_LOG_PATH = Path("ai-service/order_audit_log.jsonl")

@dataclass
class OrderAuditRecord:
    """Immutable record of every order attempt - accepted OR rejected"""
    timestamp_utc: str
    symbol: str
    direction: str
    account_id: int
    account_name: str
    
    # Risk calculation
    equity_at_decision: float
    risk_percent: float
    risk_budget_usd: float
    
    # Position sizing
    entry_price: float
    stop_loss: float
    sl_distance_pips: float
    pip_value_per_lot: float
    requested_volume: float
    approved_volume: float
    actual_risk_usd: float
    
    # Gate result
    gate_result: str  # "APPROVED" or "REJECTED"
    gate_reason: Optional[str] = None
    
    # MT5 result (if order was sent)
    mt5_order_ticket: Optional[int] = None
    mt5_position_ticket: Optional[int] = None
    mt5_retcode: Optional[int] = None
    
    def log(self):
        """Append immutable record to audit log"""
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_PATH, 'a') as f:
            f.write(json.dumps(asdict(self)) + '\n')


def log_rejected_order(symbol: str, direction: str, account_id: int, account_name: str,
                       equity: float, risk_pct: float, entry: float, sl: float,
                       volume: float, pip_value: float, reason: str) -> OrderAuditRecord:
    """Log a REJECTED order - critical for debugging 'why no trades?'"""
    sl_pips = abs(entry - sl) / 0.0001
    actual_risk = sl_pips * pip_value * volume
    budget = equity * risk_pct
    
    record = OrderAuditRecord(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        symbol=symbol, direction=direction,
        account_id=account_id, account_name=account_name,
        equity_at_decision=equity, risk_percent=risk_pct,
        risk_budget_usd=round(budget, 6),
        entry_price=entry, stop_loss=sl,
        sl_distance_pips=round(sl_pips, 1),
        pip_value_per_lot=pip_value,
        requested_volume=volume, approved_volume=0.0,
        actual_risk_usd=round(actual_risk, 2),
        gate_result="REJECTED", gate_reason=reason,
    )
    record.log()
    return record


def log_approved_order(symbol: str, direction: str, account_id: int, account_name: str,
                       equity: float, risk_pct: float, entry: float, sl: float,
                       volume: float, pip_value: float,
                       mt5_order: Optional[int] = None,
                       mt5_position: Optional[int] = None,
                       mt5_retcode: Optional[int] = None) -> OrderAuditRecord:
    """Log an APPROVED order that was sent to MT5"""
    sl_pips = abs(entry - sl) / 0.0001
    actual_risk = sl_pips * pip_value * volume
    budget = equity * risk_pct
    
    record = OrderAuditRecord(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        symbol=symbol, direction=direction,
        account_id=account_id, account_name=account_name,
        equity_at_decision=equity, risk_percent=risk_pct,
        risk_budget_usd=round(budget, 6),
        entry_price=entry, stop_loss=sl,
        sl_distance_pips=round(sl_pips, 1),
        pip_value_per_lot=pip_value,
        requested_volume=volume, approved_volume=volume,
        actual_risk_usd=round(actual_risk, 2),
        gate_result="APPROVED",
        mt5_order_ticket=mt5_order,
        mt5_position_ticket=mt5_position,
        mt5_retcode=mt5_retcode,
    )
    record.log()
    return record
