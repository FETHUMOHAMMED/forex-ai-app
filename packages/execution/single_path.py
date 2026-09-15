"""SINGLE AUTHORITATIVE EXECUTION PATH - The ONLY way to MT5."""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from packages.execution.hard_order_boundary import HardOrderBoundary, OrderRequest

class SingleExecutionPath:
    """
    THE ONLY production path to MT5.
    Uses HardOrderBoundary for validation.
    No other production file calls mt5.order_send.
    """
    
    def __init__(self):
        self.path_name = "SINGLE_EXECUTION_PATH_V2"
        self.boundary = HardOrderBoundary()  # REQUIRED - uses hard boundary
    
    def get_symbol_info(self, symbol: str):
        """Get broker symbol metadata."""
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return None
        info = mt5.symbol_info(symbol)
        mt5.shutdown()
        return info

    def get_permitted_filling_mode(self, symbol: str):
        """Get broker-permitted filling modes for symbol."""
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return None
        info = mt5.symbol_info(symbol)
        mt5.shutdown()
        if info is None:
            return None
        return info.filling_mode  # Bitmask of permitted modes

    def select_filling_mode(self, symbol: str):
        """
        Select appropriate filling mode based on broker permissions.
        Priority: IOC > FOK > RETURN (market orders)
        """
        import MetaTrader5 as mt5
        filling = self.get_permitted_filling_mode(symbol)
        if filling is None:
            return mt5.ORDER_FILLING_IOC  # Default fallback
        
        # Bitmask: 1=IOC, 2=FOK, 4=RETURN
        if filling & 1:  # IOC permitted
            return mt5.ORDER_FILLING_IOC
        elif filling & 2:  # FOK permitted
            return mt5.ORDER_FILLING_FOK
        elif filling & 4:  # RETURN permitted
            return mt5.ORDER_FILLING_RETURN
        return mt5.ORDER_FILLING_IOC  # Fallback

    def validate_symbol_state(self, order: OrderRequest) -> Tuple[bool, str]:
        """
        Validate broker symbol state before execution.
        Checks: exists, tradeable, market open, volume, stop levels.
        """
        info = self.get_symbol_info(order.symbol)
        if info is None:
            return False, f"Symbol {order.symbol} not found"
        
        if not info.visible:
            return False, f"Symbol {order.symbol} not visible"
        
        if not info.trade_mode == 4:  # 4 = MARKET_EXECUTION
            return False, f"Trade mode {info.trade_mode} not market execution"
        
        # Volume validation
        if order.volume < info.volume_min:
            return False, f"Volume {order.volume} below min {info.volume_min}"
        if order.volume > info.volume_max:
            return False, f"Volume {order.volume} above max {info.volume_max}"
        
        # Volume step validation
        volume_step = info.volume_step
        if volume_step > 0:
            steps = round((order.volume - info.volume_min) / volume_step)
            valid_volume = info.volume_min + (steps * volume_step)
            if abs(valid_volume - order.volume) > 0.0001:
                return False, f"Volume {order.volume} not aligned to step {volume_step}"
        
        # Stop level check
        stop_level = getattr(info, "stops_level", 0)  # 0 if not available
        if stop_level > 0:
            sl_distance = abs(order.entry - order.sl) / 0.01
            if sl_distance < stop_level:
                return False, f"SL distance {sl_distance:.1f} pips below stop level {stop_level}"
        
        return True, f"Symbol OK: mode={info.trade_mode}, vol=[{info.volume_min}-{info.volume_max}] step={info.volume_step}"

    def get_current_market_tick(self, symbol: str):
        """Get CURRENT market price before execution."""
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return None
        tick = mt5.symbol_info_tick(symbol)
        mt5.shutdown()
        return tick

    def validate_current_market(self, order: OrderRequest) -> Tuple[bool, str]:
        """
        FINAL pre-send check: Validate against CURRENT market, not stale signal.
        Rejects if market moved significantly from signal price.
        """
        tick = self.get_current_market_tick(order.symbol)
        if tick is None:
            return False, "Cannot get current market tick"
        
        current_ask = tick.ask
        current_bid = tick.bid
        current_spread = (current_ask - current_bid) / 0.01  # pips
        
        # Check price deviation from signal (max 5 pips)
        deviation = abs(current_ask - order.entry) / 0.01
        if deviation > 5.0:
            return False, f"Price moved {deviation:.1f} pips from signal (max 5)"
        
        # Check spread (max 3 pips)
        if current_spread > 3.0:
            return False, f"Spread {current_spread:.1f} pips too high (max 3)"
        
        return True, f"Market OK: ask={current_ask}, spread={current_spread:.1f} pips"

    def execute_order(self, order: OrderRequest, mode: str = "PAPER") -> Dict:
        """
        Execute order through HardOrderBoundary validation.
        mode: "PAPER" (no real order) or "LIVE" (real MT5 order)
        """
        # Step 1: Validate through HARD BOUNDARY (mandatory)
        is_valid, checks = self.boundary.validate_order(order)
        
        # Step 1.5: FINAL current market check (for LIVE mode)
        market_ok = True
        market_reason = ""
        if mode == "LIVE":
            symbol_ok, symbol_reason = self.validate_symbol_state(order)
            if not symbol_ok:
                return {
                    "status": "REJECTED_SYMBOL",
                    "checks": checks,
                    "mt5_called": False,
                    "reason": symbol_reason
                }
            
            market_ok, market_reason = self.validate_current_market(order)
            if not market_ok:
                return {
                    "status": "REJECTED_MARKET",
                    "checks": checks,
                    "mt5_called": False,
                    "reason": market_reason
                }
        
        if not is_valid:
            return {
                "status": "REJECTED",
                "checks": checks,
                "mt5_called": False,
                "reason": "HardOrderBoundary validation failed"
            }
        
        # Step 2: Execute based on mode
        if mode == "PAPER":
            return {
                "status": "PAPER_EXECUTED",
                "checks": checks,
                "mt5_called": False,
                "order": order.__dict__
            }
        
        elif mode == "LIVE":
            import MetaTrader5 as mt5
            
            if not mt5.initialize():
                return {
                    "status": "ERROR",
                    "reason": "MT5 init failed",
                    "mt5_called": False
                }
            
            # Construct order with VALIDATED values
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": order.symbol,
                "volume": order.volume,
                "type": mt5.ORDER_TYPE_BUY,  # BUY only enforced by boundary
                "price": order.entry,
                "sl": order.sl,
                "tp": order.tp,
                "deviation": 20,
                "magic": 123456,
                "comment": "V4_CANONICAL_1.0",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": self.select_filling_mode(order.symbol),  # Dynamic from broker
            }
            
            # THE ONLY mt5.order_send in production
            result = mt5.order_send(request)
            mt5.shutdown()
            
            # Structured execution result
            execution_result = {
                "retcode": result.retcode if result else None,
                "order_ticket": result.order if result else None,
                "deal_ticket": result.deal if result else None,
                "request_id": result.request_id if result else None,
                "broker_comment": result.comment if result else None,
                "execution_price": result.price if result else None,
                "requested_price": order.entry,
                "volume": order.volume,
                "sl": order.sl,
                "tp": order.tp,
                "request": request
            }
            
            return {
                "status": "LIVE_EXECUTED" if result and result.retcode == mt5.TRADE_RETCODE_DONE else "LIVE_FAILED",
                "checks": checks,
                "mt5_called": True,
                "execution": execution_result
            }
        
        return {"status": "INVALID_MODE", "mt5_called": False}

if __name__ == "__main__":
    path = SingleExecutionPath()
    
    print("="*70)
    print("  SINGLE EXECUTION PATH (V2 - Uses HardOrderBoundary)")
    print("="*70)
    
    # Test with valid order
    valid_order = OrderRequest(
        symbol="USDJPYm",
        direction="BUY",
        volume=0.01,
        entry=154.250,
        sl=154.210,
        tp=154.330,
        risk_percent=0.25,
        account="REDACTED_LIVE_ACCOUNT",
        strategy_version="V4_CANONICAL_1.0"
    )
    
    print(f"\n  TEST: Valid order (paper mode)")
    result = path.execute_order(valid_order, mode="PAPER")
    print(f"    Status: {result['status']}")
    print(f"    MT5 called: {result['mt5_called']}")
    
    # Test with invalid order
    bad_order = OrderRequest(
        symbol="EURUSDm",
        direction="SELL",
        volume=0.01,
        entry=1.1575,
        sl=0,
        tp=0,
        risk_percent=10.0,
        account="wrong",
        strategy_version="OLD"
    )
    
    print(f"\n  TEST: Invalid order (live mode)")
    result = path.execute_order(bad_order, mode="LIVE")
    print(f"    Status: {result['status']}")
    print(f"    MT5 called: {result['mt5_called']}")
    print(f"    Reason: {result.get('reason', 'N/A')}")






