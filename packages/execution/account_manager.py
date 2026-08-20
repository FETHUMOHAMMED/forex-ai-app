"""Isolated Account Manager - Each account gets its own MT5 session.
Prevents race conditions and state contamination from shared global MT5 state.

Architecture:
    AccountManager
       |
       +-- AccountWorker("Live_Micro", REDACTED_LIVE_ACCOUNT)
       |      +-- Own MT5 session
       |      +-- Own broker instance
       |      +-- Own trade logger
       |
       +-- AccountWorker("Demo2", REDACTED_DEMO_ACCOUNT)
       |      +-- Own MT5 session
       |      +-- Own broker instance
       |      +-- Own trade logger
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import threading
import time

class AccountStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    TRADING = "TRADING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"

@dataclass
class AccountConfig:
    """Immutable account configuration"""
    name: str
    account_id: int
    server: str
    pairs: List[str]
    risk_percent: float          # e.g., 0.0005 for 0.05%
    max_daily_trades: int
    max_daily_loss_pct: float
    is_enabled: bool = True
    environment: str = "LIVE_MICRO"  # "LIVE_MICRO", "DEMO", "VALIDATION"

@dataclass
class AccountWorker:
    """Isolated worker for ONE account - owns its MT5 session.
    
    CRITICAL: Never share MT5 state between workers.
    Each worker initializes and manages its own connection.
    """
    config: AccountConfig
    status: AccountStatus = AccountStatus.DISCONNECTED
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    # Per-worker state (isolated - no sharing!)
    _mt5_connected: bool = False
    _last_heartbeat: float = 0.0
    _daily_trades: int = 0
    _daily_pnl: float = 0.0
    _positions: List[dict] = field(default_factory=list)
    
    def connect(self) -> bool:
        """Initialize MT5 connection for THIS account only.
        Must be called from this worker's thread.
        """
        with self._lock:
            self.status = AccountStatus.CONNECTING
            
            import MetaTrader5 as mt5
            if not mt5.initialize():
                self.status = AccountStatus.ERROR
                return False
            
            # Login to THIS account specifically
            authorized = mt5.login(
                login=self.config.account_id,
                server=self.config.server,
            )
            
            if not authorized:
                self.status = AccountStatus.ERROR
                mt5.shutdown()
                return False
            
            self._mt5_connected = True
            self.status = AccountStatus.CONNECTED
            return True
    
    def disconnect(self):
        """Clean shutdown of this worker's MT5 session"""
        with self._lock:
            import MetaTrader5 as mt5
            mt5.shutdown()
            self._mt5_connected = False
            self.status = AccountStatus.DISCONNECTED
    
    def get_account_info(self) -> Optional[dict]:
        """Get account info from THIS worker's MT5 session"""
        with self._lock:
            if not self._mt5_connected:
                return None
            import MetaTrader5 as mt5
            info = mt5.account_info()
            if info:
                return {
                    "balance": info.balance,
                    "equity": info.equity,
                    "margin": info.margin,
                    "free_margin": info.margin_free,
                    "server": info.server,
                }
        return None
    
    def get_positions(self) -> List[dict]:
        """Get positions from THIS worker's MT5 session"""
        with self._lock:
            if not self._mt5_connected:
                return []
            import MetaTrader5 as mt5
            positions = mt5.positions_get()
            if positions:
                return [{
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == 0 else "SELL",
                    "volume": p.volume,
                    "open_price": p.price_open,
                    "current_price": p.price_current,
                    "sl": p.sl,
                    "tp": p.tp,
                    "profit": p.profit,
                } for p in positions]
        return []
    
    def place_order(self, symbol: str, order_type: str, volume: float,
                    price: float, sl: float, tp: float) -> Optional[dict]:
        """Place order in THIS worker's MT5 session.
        
        Args:
            symbol: Trading symbol
            order_type: "BUY" or "SELL"
            volume: Lot size
            price: Entry price (market order = current price)
            sl: Stop loss price
            tp: Take profit price
        
        Returns:
            dict with order_ticket, position_ticket, retcode on success
            None on failure
        """
        with self._lock:
            if not self._mt5_connected:
                return None
            
            import MetaTrader5 as mt5
            
            # Prepare request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 30,
                "magic": 234000,
                "comment": f"AI_{self.config.name}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                # Get the position ticket
                positions = mt5.positions_get(symbol=symbol)
                pos_ticket = max(p.ticket for p in positions) if positions else None
                
                return {
                    "order_ticket": result.order,
                    "position_ticket": pos_ticket,
                    "deal_ticket": result.deal,
                    "retcode": result.retcode,
                    "volume": result.volume,
                    "price": result.price,
                }
            
            return {
                "retcode": result.retcode if result else -1,
                "comment": result.comment if result else "Unknown error",
                "error": True,
            }
    
    def heartbeat(self):
        """Update heartbeat timestamp"""
        self._last_heartbeat = time.time()
    
    @property
    def heartbeat_age_seconds(self) -> float:
        return time.time() - self._last_heartbeat
    
    @property
    def is_healthy(self) -> bool:
        return self._mt5_connected and self.heartbeat_age_seconds < 120


@dataclass
class AccountManager:
    """Manages multiple isolated account workers.
    
    Each account gets its own worker with its own MT5 session.
    Workers do NOT share state. No global MT5 switching.
    """
    workers: Dict[str, AccountWorker] = field(default_factory=dict)
    
    def add_account(self, config: AccountConfig) -> AccountWorker:
        """Register a new account with its own isolated worker"""
        if config.name in self.workers:
            raise ValueError(f"Account {config.name} already registered")
        
        worker = AccountWorker(config=config)
        self.workers[config.name] = worker
        return worker
    
    def get_worker(self, account_name: str) -> Optional[AccountWorker]:
        """Get worker for a specific account"""
        return self.workers.get(account_name)
    
    def connect_all(self) -> Dict[str, bool]:
        """Connect all enabled accounts"""
        results = {}
        for name, worker in self.workers.items():
            if worker.config.is_enabled:
                results[name] = worker.connect()
        return results
    
    def disconnect_all(self):
        """Disconnect all workers"""
        for worker in self.workers.values():
            worker.disconnect()
    
    def get_all_positions(self) -> Dict[str, List[dict]]:
        """Get positions from all accounts"""
        return {
            name: worker.get_positions()
            for name, worker in self.workers.items()
            if worker._mt5_connected
        }
    
    def health_report(self) -> dict:
        """Health status of all accounts"""
        return {
            name: {
                "status": worker.status.value,
                "healthy": worker.is_healthy,
                "heartbeat_age": worker.heartbeat_age_seconds,
                "daily_trades": worker._daily_trades,
            }
            for name, worker in self.workers.items()
        }


# ============================================================================
# CONFIGURATION - Define all accounts here
# ============================================================================

ACCOUNTS = {
    "Live_Micro": AccountConfig(
        name="Live_Micro",
        account_id=REDACTED_LIVE_ACCOUNT,
        server="Exness-MT5Real10",
        pairs=["EURUSD"],
        risk_percent=0.0005,       # 0.05% risk per trade
        max_daily_trades=5,
        max_daily_loss_pct=0.05,   # 5% max daily loss
        environment="LIVE_MICRO_VALIDATION",
        is_enabled=True,
    ),
    "Demo2": AccountConfig(
        name="Demo2",
        account_id=REDACTED_DEMO_ACCOUNT,
        server="Exness-MT5Trial9",
        pairs=["EURUSD"],
        risk_percent=0.01,          # 1% risk for data collection
        max_daily_trades=8,
        max_daily_loss_pct=0.10,    # 10% max daily loss
        environment="DEMO",
        is_enabled=True,
    ),
}
