"""Execution Adapter Protocol - Strategy doesn't know which broker."""
from typing import Protocol, List, Optional, Dict
from datetime import datetime

class ExecutionAdapter(Protocol):
    """THE execution contract. All broker adapters implement this."""
    
    def submit_order(self, order: dict) -> dict:
        """Submit order. Returns order_result."""
        ...
    
    def cancel_order(self, order_id: str) -> dict:
        """Cancel order."""
        ...
    
    def modify_order(self, order_id: str, modifications: dict) -> dict:
        """Modify existing order (SL/TP changes, etc.)."""
        ...
    
    def get_positions(self) -> List[dict]:
        """Get all open positions."""
        ...
    
    def get_orders(self) -> List[dict]:
        """Get all pending orders."""
        ...
    
    def get_deals(self, from_time: datetime, to_time: datetime) -> List[dict]:
        """Get deal history."""
        ...


class MT5ExecutionAdapter:
    """MT5 adapter - current implementation."""
    
    def __init__(self):
        import MetaTrader5 as mt5
        self.mt5 = mt5
    
    def submit_order(self, order: dict) -> dict:
        self.mt5.initialize()
        result = self.mt5.order_send(order)
        self.mt5.shutdown()
        return {
            "retcode": result.retcode if result else -1,
            "order_ticket": result.order if result else None,
            "comment": result.comment if result else "No result",
        }
    
    def cancel_order(self, order_id: str) -> dict:
        self.mt5.initialize()
        result = self.mt5.order_send({
            "action": self.mt5.TRADE_ACTION_REMOVE,
            "order": int(order_id),
        })
        self.mt5.shutdown()
        return {"retcode": result.retcode if result else -1}
    
    def modify_order(self, order_id: str, modifications: dict) -> dict:
        self.mt5.initialize()
        result = self.mt5.order_send({
            "action": self.mt5.TRADE_ACTION_SLTP,
            "position": int(order_id),
            **modifications,
        })
        self.mt5.shutdown()
        return {"retcode": result.retcode if result else -1}
    
    def get_positions(self) -> List[dict]:
        self.mt5.initialize()
        positions = self.mt5.positions_get()
        self.mt5.shutdown()
        if not positions:
            return []
        return [{
            "ticket": p.ticket, "symbol": p.symbol,
            "direction": "BUY" if p.type == 0 else "SELL",
            "volume": p.volume, "entry": p.price_open,
            "sl": p.sl, "tp": p.tp, "profit": p.profit,
        } for p in positions]
    
    def get_orders(self) -> List[dict]:
        self.mt5.initialize()
        orders = self.mt5.orders_get()
        self.mt5.shutdown()
        if not orders:
            return []
        return [{"ticket": o.ticket, "symbol": o.symbol} for o in orders]
    
    def get_deals(self, from_time: datetime, to_time: datetime) -> List[dict]:
        self.mt5.initialize()
        deals = self.mt5.history_deals_get(from_time, to_time)
        self.mt5.shutdown()
        if not deals:
            return []
        return [{
            "ticket": d.ticket, "position_id": d.position_id,
            "entry": d.entry, "price": d.price,
            "profit": d.profit, "time": d.time,
        } for d in deals]


class FixExecutionAdapter:
    """FIX protocol adapter - FUTURE implementation."""
    
    def __init__(self):
        raise NotImplementedError("FIX adapter not yet implemented")
    
    def submit_order(self, order: dict) -> dict:
        raise NotImplementedError("FIX protocol requires network infrastructure")
    
    def cancel_order(self, order_id: str) -> dict:
        raise NotImplementedError("FIX protocol requires network infrastructure")
    
    def modify_order(self, order_id: str, modifications: dict) -> dict:
        raise NotImplementedError("FIX protocol requires network infrastructure")
    
    def get_positions(self) -> List[dict]:
        raise NotImplementedError("FIX protocol requires network infrastructure")
    
    def get_orders(self) -> List[dict]:
        raise NotImplementedError("FIX protocol requires network infrastructure")
    
    def get_deals(self, from_time: datetime, to_time: datetime) -> List[dict]:
        raise NotImplementedError("FIX protocol requires network infrastructure")


class BrokerAPIExecutionAdapter:
    """REST API broker adapter - FUTURE implementation."""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
    
    def submit_order(self, order: dict) -> dict:
        raise NotImplementedError("REST API broker requires endpoint configuration")
    
    def cancel_order(self, order_id: str) -> dict:
        raise NotImplementedError("REST API broker requires endpoint configuration")
    
    def modify_order(self, order_id: str, modifications: dict) -> dict:
        raise NotImplementedError("REST API broker requires endpoint configuration")
    
    def get_positions(self) -> List[dict]:
        raise NotImplementedError("REST API broker requires endpoint configuration")
    
    def get_orders(self) -> List[dict]:
        raise NotImplementedError("REST API broker requires endpoint configuration")
    
    def get_deals(self, from_time: datetime, to_time: datetime) -> List[dict]:
        raise NotImplementedError("REST API broker requires endpoint configuration")


# ============================================================================
# THE FACTORY - Strategy doesn't know which adapter it's using
# ============================================================================

def get_execution_adapter(broker_type: str = "MT5", **kwargs) -> ExecutionAdapter:
    """
    THE factory. Strategy calls this, gets an adapter.
    Strategy doesn't know if it's MT5, FIX, or REST API.
    """
    adapters = {
        "MT5": MT5ExecutionAdapter,
        "FIX": FixExecutionAdapter,
        "REST": BrokerAPIExecutionAdapter,
    }
    
    adapter_class = adapters.get(broker_type.upper())
    if not adapter_class:
        raise ValueError(f"Unknown broker type: {broker_type}")
    
    if broker_type.upper() == "REST":
        return adapter_class(kwargs.get("api_url", ""), kwargs.get("api_key", ""))
    return adapter_class()


if __name__ == "__main__":
    print("=" * 65)
    print("  EXECUTION ADAPTER PROTOCOL")
    print("=" * 65)
    
    # Get MT5 adapter
    adapter = get_execution_adapter("MT5")
    print(f"\n  Using: {type(adapter).__name__}")
    positions = adapter.get_positions()
    print(f"  Positions: {len(positions)}")
    
    # Strategy doesn't know it's MT5
    print(f"\n  STRATEGY VIEW:")
    print(f"    Strategy calls: adapter.submit_order(...)")
    print(f"    Strategy doesn't know: MT5 or FIX or REST")
    print(f"    Adapter type: {type(adapter).__name__}")
    
    print(f"\n  FUTURE ADAPTERS:")
    print(f"    - FIX: FIX protocol for institutional brokers")
    print(f"    - REST: Broker API (e.g., OANDA, Interactive Brokers)")
    print(f"    - MT5: Current implementation")
    
    print(f"\n{'='*65}")
