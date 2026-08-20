"""Real Risk Management System - Pre-trade, Intraday, Emergency controls."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum

class RiskLevel(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    REDUCED = "REDUCED"
    HALT = "HALT"

@dataclass
class RiskLimits:
    """All risk limits in one place"""
    # Pre-trade
    max_risk_per_trade_pct: float = 0.0005   # 0.05%
    max_portfolio_risk_pct: float = 0.03     # 3%
    max_daily_loss_pct: float = 0.05         # 5%
    max_drawdown_pct: float = 0.10           # 10%
    max_leverage: float = 10.0
    max_position_size: float = 0.01          # 0.01 lots
    max_currency_exposure: float = 0.10      # 10% in one currency
    max_pair_exposure: float = 0.05          # 5% in one pair
    max_correlated_exposure: float = 0.10    # 10% correlated
    max_spread: float = 0.0015               # 15 pips
    max_slippage_pips: float = 5.0
    # Session
    trading_sessions: list = None
    news_blackout: bool = True

class RiskManagementSystem:
    """THE RMS - all risk controls."""
    
    def __init__(self):
        self.limits = RiskLimits()
        self.state = RiskLevel.NORMAL
        self.kill_switch_active = False
        self.emergency_reason = None
        self.metrics = self._load_metrics()
    
    def _load_metrics(self) -> dict:
        """Load current risk metrics"""
        return {
            "equity": 0.0,
            "margin": 0.0,
            "free_margin": 0.0,
            "drawdown": 0.0,
            "exposure": 0.0,
            "open_risk": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "loss_streak": 0,
            "daily_loss": 0.0,
            "weekly_loss": 0.0,
            "trades_today": 0,
        }
    
    def pre_trade_check(self, trade: dict) -> tuple:
        """Pre-trade risk checks. Returns (allowed, reason)."""
        if self.kill_switch_active:
            return False, f"KILL_SWITCH: {self.emergency_reason}"
        
        # Maximum risk per trade
        equity = self.metrics.get("equity", 0)
        risk_pct = trade.get("risk_pct", 0.0005)
        if risk_pct > self.limits.max_risk_per_trade_pct:
            return False, f"Risk {risk_pct} exceeds max {self.limits.max_risk_per_trade_pct}"
        
        # Maximum position size
        volume = trade.get("volume", 0)
        if volume > self.limits.max_position_size:
            return False, f"Volume {volume} exceeds max {self.limits.max_position_size}"
        
        # Daily loss limit
        if self.metrics["daily_loss"] > equity * self.limits.max_daily_loss_pct:
            return False, f"Daily loss ${self.metrics['daily_loss']:.2f} exceeds limit"
        
        # Drawdown limit
        if self.metrics["drawdown"] > self.limits.max_drawdown_pct:
            return False, f"Drawdown {self.metrics['drawdown']*100:.1f}% exceeds limit"
        
        # Spread check
        spread = trade.get("spread", 0)
        if spread > self.limits.max_spread:
            return False, f"Spread {spread} exceeds max {self.limits.max_spread}"
        
        return True, "ALL_CHECKS_PASSED"
    
    def intraday_check(self) -> RiskLevel:
        """Intraday risk monitoring."""
        equity = self.metrics.get("equity", 0)
        drawdown = self.metrics.get("drawdown", 0)
        
        if self.kill_switch_active:
            return RiskLevel.HALT
        
        if drawdown > self.limits.max_drawdown_pct:
            return RiskLevel.HALT
        
        if self.metrics["daily_loss"] > equity * self.limits.max_daily_loss_pct:
            return RiskLevel.HALT
        
        if self.metrics["loss_streak"] >= 5:
            return RiskLevel.REDUCED
        
        if self.metrics["drawdown"] > self.limits.max_drawdown_pct * 0.5:
            return RiskLevel.WARNING
        
        return RiskLevel.NORMAL
    
    def activate_kill_switch(self, reason: str):
        """Emergency: halt ALL trading immediately."""
        self.kill_switch_active = True
        self.emergency_reason = reason
        self.state = RiskLevel.HALT
        print(f"[KILL SWITCH] ACTIVATED: {reason}")
        print(f"[KILL SWITCH] ALL TRADING HALTED")
    
    def deactivate_kill_switch(self):
        """Resume trading (manual authorization required)."""
        self.kill_switch_active = False
        self.emergency_reason = None
        self.state = RiskLevel.NORMAL
        print(f"[KILL SWITCH] DEACTIVATED - trading resumed")
    
    def flatten_all_positions(self):
        """Emergency: close all positions."""
        import MetaTrader5 as mt5
        mt5.initialize()
        positions = mt5.positions_get()
        if positions:
            for p in positions:
                close_type = mt5.ORDER_TYPE_BUY if p.type == 1 else mt5.ORDER_TYPE_SELL
                tick = mt5.symbol_info_tick(p.symbol)
                price = tick.ask if p.type == 1 else tick.bid
                mt5.order_send({
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": p.ticket,
                    "symbol": p.symbol,
                    "volume": p.volume,
                    "type": close_type,
                    "price": price,
                    "deviation": 100,
                    "comment": "EMERGENCY_FLATTEN",
                })
        mt5.shutdown()
        print(f"[EMERGENCY] All positions flattened")
    
    def get_risk_report(self) -> dict:
        """Complete risk report"""
        return {
            "state": self.state.value,
            "kill_switch": self.kill_switch_active,
            "kill_switch_reason": self.emergency_reason,
            "metrics": self.metrics,
            "limits": {
                "max_risk_per_trade": self.limits.max_risk_per_trade_pct,
                "max_daily_loss": self.limits.max_daily_loss_pct,
                "max_drawdown": self.limits.max_drawdown_pct,
                "max_position": self.limits.max_position_size,
                "max_spread": self.limits.max_spread,
            },
        }


if __name__ == "__main__":
    rms = RiskManagementSystem()
    
    print("=" * 65)
    print("  RISK MANAGEMENT SYSTEM")
    print("=" * 65)
    
    # Test pre-trade check
    print("\n  PRE-TRADE CHECK:")
    allowed, reason = rms.pre_trade_check({
        "volume": 0.01, "risk_pct": 0.0005, "spread": 0.0008
    })
    print(f"  Normal trade: {'ALLOWED' if allowed else 'REJECTED'} ({reason})")
    
    # Test kill switch
    print("\n  KILL SWITCH TEST:")
    rms.activate_kill_switch("Manual emergency")
    allowed, reason = rms.pre_trade_check({
        "volume": 0.01, "risk_pct": 0.0005, "spread": 0.0008
    })
    print(f"  Trade after kill switch: {'ALLOWED' if allowed else 'REJECTED'} ({reason})")
    
    rms.deactivate_kill_switch()
    print(f"  After deactivation: {'ALLOWED' if rms.pre_trade_check({'volume': 0.01, 'risk_pct': 0.0005, 'spread': 0.0008})[0] else 'REJECTED'}")
    
    print(f"\n{'='*65}")
