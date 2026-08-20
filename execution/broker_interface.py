"""
Phase 6: Broker Interface - Abstract broker, injectable dependencies.
Signal pipeline never touches MT5 directly. Execution never touches ML.
Swap MT5 for OANDA/Binance/Paper without changing any trading logic.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class OrderResult:
    success: bool
    ticket: int = 0
    price: float = 0.0
    volume: float = 0.0
    error: str = ""


@dataclass
class Position:
    ticket: int
    symbol: str
    direction: str  # BUY or SELL
    volume: float
    entry: float
    sl: float = 0.0
    tp: float = 0.0
    profit: float = 0.0
    open_time: str = ""


class BrokerInterface(ABC):
    """Abstract broker - all brokers implement this."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to broker. Returns True if successful."""
        ...
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from broker."""
        ...
    
    @abstractmethod
    def get_balance(self) -> float:
        """Get account balance."""
        ...
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get all open positions."""
        ...
    
    @abstractmethod
    def execute_market_order(self, symbol: str, direction: str, volume: float,
                             sl: float, tp: float, comment: str = "") -> OrderResult:
        """Execute a market order with SL/TP."""
        ...
    
    @abstractmethod
    def close_position(self, ticket: int) -> OrderResult:
        """Close a specific position."""
        ...
    
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol specifications (min volume, pip size, etc)."""
        ...
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current bid/ask for a symbol."""
        ...


class MT5Broker(BrokerInterface):
    """MT5 implementation of BrokerInterface."""
    
    def __init__(self, account: int, password: str, server: str):
        self.account = account
        self.password = password
        self.server = server
        self._mt5 = None
    
    def connect(self) -> bool:
        import MetaTrader5 as mt5
        self._mt5 = mt5
        if not self._mt5.initialize():
            return False
        return self._mt5.login(self.account, password=self.password, server=self.server)
    
    def disconnect(self):
        if self._mt5:
            self._mt5.shutdown()
    
    def get_balance(self) -> float:
        info = self._mt5.account_info()
        return info.balance if info else 0.0
    
    def get_positions(self) -> List[Position]:
        positions = self._mt5.positions_get()
        if not positions:
            return []
        return [Position(
            ticket=p.ticket,
            symbol=p.symbol.replace('m', ''),
            direction='BUY' if p.type == 0 else 'SELL',
            volume=p.volume,
            entry=p.price_open,
            sl=p.sl,
            tp=p.tp,
            profit=p.profit,
            open_time=datetime.fromtimestamp(p.time, tz=timezone.utc).isoformat(),
        ) for p in positions]
    
    def execute_market_order(self, symbol: str, direction: str, volume: float,
                             sl: float, tp: float, comment: str = "") -> OrderResult:
        sym = symbol + 'm'
        self._mt5.symbol_select(sym, True)
        
        tick = self._mt5.symbol_info_tick(sym)
        if not tick:
            return OrderResult(success=False, error="No tick data")
        
        order_type = self._mt5.ORDER_TYPE_BUY if direction == 'BUY' else self._mt5.ORDER_TYPE_SELL
        price = tick.ask if direction == 'BUY' else tick.bid
        
        request = {
            'action': self._mt5.TRADE_ACTION_DEAL,
            'symbol': sym,
            'volume': volume,
            'type': order_type,
            'price': price,
            'sl': sl,
            'tp': tp,
            'deviation': 20,
            'magic': 0,
            'comment': comment,
            'type_time': self._mt5.ORDER_TIME_GTC,
            'type_filling': self._mt5.ORDER_FILLING_IOC,
        }
        
        result = self._mt5.order_send(request)
        if result.retcode == self._mt5.TRADE_RETCODE_DONE:
            return OrderResult(success=True, ticket=result.order, price=result.price, volume=volume)
        return OrderResult(success=False, error=f"MT5 retcode={result.retcode} {result.comment}")
    
    def close_position(self, ticket: int) -> OrderResult:
        positions = self._mt5.positions_get(ticket=ticket)
        if not positions:
            return OrderResult(success=False, error="Position not found")
        p = positions[0]
        
        order_type = self._mt5.ORDER_TYPE_SELL if p.type == 0 else self._mt5.ORDER_TYPE_BUY
        tick = self._mt5.symbol_info_tick(p.symbol)
        price = tick.bid if p.type == 0 else tick.ask
        
        request = {
            'action': self._mt5.TRADE_ACTION_DEAL,
            'symbol': p.symbol,
            'volume': p.volume,
            'type': order_type,
            'position': ticket,
            'price': price,
            'deviation': 20,
            'magic': 0,
            'comment': 'AI_close',
            'type_time': self._mt5.ORDER_TIME_GTC,
            'type_filling': self._mt5.ORDER_FILLING_IOC,
        }
        
        result = self._mt5.order_send(request)
        return OrderResult(success=result.retcode == self._mt5.TRADE_RETCODE_DONE, ticket=ticket, price=result.price if result else 0)
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        info = self._mt5.symbol_info(symbol + 'm')
        if not info:
            return None
        return {'min_volume': info.volume_min, 'max_volume': info.volume_max, 'digits': info.digits}
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        tick = self._mt5.symbol_info_tick(symbol + 'm')
        return (tick.bid + tick.ask) / 2 if tick else None


class PaperBroker(BrokerInterface):
    """Paper trading broker for testing - no real money."""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.positions: List[Position] = []
        self._next_ticket = 1000000
    
    def connect(self) -> bool:
        return True
    
    def disconnect(self):
        pass
    
    def get_balance(self) -> float:
        return self.balance
    
    def get_positions(self) -> List[Position]:
        return self.positions
    
    def execute_market_order(self, symbol: str, direction: str, volume: float,
                             sl: float, tp: float, comment: str = "") -> OrderResult:
        ticket = self._next_ticket
        self._next_ticket += 1
        self.positions.append(Position(
            ticket=ticket, symbol=symbol, direction=direction,
            volume=volume, entry=0, sl=sl, tp=tp,
            open_time=datetime.now(timezone.utc).isoformat()
        ))
        return OrderResult(success=True, ticket=ticket)
    
    def close_position(self, ticket: int) -> OrderResult:
        self.positions = [p for p in self.positions if p.ticket != ticket]
        return OrderResult(success=True, ticket=ticket)
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        return {'min_volume': 0.01, 'max_volume': 100.0, 'digits': 5}
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        return 1.0


if __name__ == '__main__':
    # Test with paper broker (no MT5 needed)
    broker = PaperBroker(10000)
    broker.connect()
    print(f"Balance: ${broker.get_balance()}")
    
    result = broker.execute_market_order('EURUSD', 'SELL', 0.01, 1.10, 1.08, 'test')
    print(f"Order: {'OK' if result.success else 'FAIL'} ticket={result.ticket}")
    
    positions = broker.get_positions()
    print(f"Positions: {len(positions)}")
    
    broker.close_position(result.ticket)
    print(f"After close: {len(broker.get_positions())} positions")
