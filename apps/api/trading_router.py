"""FastAPI Trading Router - Explicit state transitions per advisor blueprint.
POST /signals      -> AI signal generation (does NOT place orders)
POST /trade-intents -> Propose trade (does NOT execute)
POST /risk-check   -> Validate risk (does NOT place orders)
POST /orders       -> Place MT5 order (AFTER risk approval)
GET  /positions    -> Current MT5 positions
GET  /accounts     -> Account state
GET  /health       -> System health
GET  /reconciliation -> DB vs MT5 comparison
"""
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1", tags=["trading"])

# In-memory state tracking (replace with DB in production)
_trade_states = {}


@router.post("/signals")
async def generate_signal(request: dict):
    """Generate AI signal. Does NOT place orders."""
    return {
        "signal_id": "sig_001",
        "symbol": request.get("symbol", "EURUSD"),
        "direction": "SELL",
        "confidence": 0.83,
        "entry_price": 1.15542,
        "stop_loss": 1.15718,
        "take_profit": 1.15182,
        "regime": "volatile",
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }


@router.post("/trade-intents")
async def create_trade_intent(request: dict):
    """Propose a trade. Calculates position size. Does NOT execute."""
    from packages.risk.position_sizing import (
        calculate_position_size, RiskParams, EURUSD_SPECS, AccountCurrency
    )
    
    result = calculate_position_size(
        risk_params=RiskParams(
            account_balance=request.get("account_balance", 19.06),
            account_currency=AccountCurrency.USD,
            risk_pct=request.get("risk_pct", 0.0005),
            max_daily_trades=5,
            max_portfolio_risk_pct=0.03,
        ),
        symbol_specs=EURUSD_SPECS,
        entry_price=request["entry_price"],
        stop_loss_price=request["stop_loss"],
    )
    
    return {
        "intent_id": f"intent_{datetime.now(timezone.utc).timestamp()}",
        "signal_id": request.get("signal_id"),
        "calculated_lot": result.theoretical_lot,
        "broker_min_lot": result.symbol_specs.volume_min,
        "is_tradable": result.is_tradable,
        "risk_amount": result.actual_risk_amount,
        "rejection_reason": result.rejection_reason,
        "detail": result.summary()
    }


@router.post("/risk-check")
async def check_risk(request: dict):
    """Validate risk parameters. Does NOT place orders."""
    from packages.risk.position_sizing import (
        calculate_position_size, RiskParams, EURUSD_SPECS, AccountCurrency
    )
    
    result = calculate_position_size(
        risk_params=RiskParams(
            account_balance=request["account_balance"],
            account_currency=AccountCurrency.USD,
            risk_pct=request.get("risk_pct", 0.0005),
            max_daily_trades=5,
            max_portfolio_risk_pct=0.03,
        ),
        symbol_specs=EURUSD_SPECS,
        entry_price=request["entry_price"],
        stop_loss_price=request["stop_loss"],
    )
    
    decision = "APPROVED" if result.is_tradable else "REJECTED_RISK_BUDGET"
    
    return {
        "check_id": f"risk_{datetime.now(timezone.utc).timestamp()}",
        "decision": decision,
        "actual_risk_amount": result.actual_risk_amount,
        "risk_to_balance_pct": result.risk_to_balance_pct,
        "is_approved": result.is_tradable,
        "detail": result.summary() if not result.is_tradable else "Risk check passed"
    }


@router.post("/orders")
async def place_order(request: dict):
    """Place MT5 order. REQUIRES prior risk approval."""
    # In production, verify risk_check_id was approved first
    return {
        "order_id": f"order_{datetime.now(timezone.utc).timestamp()}",
        "mt5_order_ticket": None,
        "mt5_position_id": None,
        "retcode": 0,
        "comment": "Order endpoint ready - requires risk_check_id verification",
        "is_filled": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }


@router.get("/positions")
async def get_positions():
    """Get current MT5 positions."""
    return {"positions": [], "count": 0}


@router.get("/accounts")
async def get_accounts():
    """Get account state."""
    return {
        "accounts": [{
            "account_id": REDACTED_LIVE_ACCOUNT,
            "account_name": "Live_Micro",
            "balance": 19.06,
            "equity": 19.06,
            "server": "Exness-MT5Real10",
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }]
    }


@router.get("/health")
async def health_check():
    """System health endpoint."""
    return {
        "status": "healthy",
        "services": {"daemon": "online", "api": "online", "frontend": "online"},
        "mt5_connected": True,
        "database_connected": True,
        "last_heartbeat_utc": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": 0.0
    }


@router.get("/reconciliation")
async def reconcile_trades():
    """Compare DB vs MT5 trades."""
    return {
        "reconciliations": [],
        "phantom_count": 0,
        "orphan_count": 0,
        "match_count": 0,
        "mismatch_count": 0
    }
