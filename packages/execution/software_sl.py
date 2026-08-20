"""Software Stop Loss - Monitors positions and closes if no broker SL exists.
Emergency protection when exchange mode rejects SL/TP.
"""
import MetaTrader5 as mt5
import time
from datetime import datetime, timezone

class SoftwareStopLoss:
    """Monitors positions every second. Closes if loss exceeds threshold."""
    
    def __init__(self, max_loss_pips=30):
        self.max_loss_pips = max_loss_pips
    
    def monitor_position(self, ticket: int, entry_price: float, direction: str):
        """Monitor ONE position. Close if loss > max_loss_pips."""
        mt5.initialize()
        
        while True:
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                print(f"[SOFT_SL] Position {ticket} closed")
                break
            
            p = positions[0]
            current_price = p.price_current
            
            if direction == 'SELL':
                loss_pips = (current_price - entry_price) / 0.0001
            else:
                loss_pips = (entry_price - current_price) / 0.0001
            
            if loss_pips > self.max_loss_pips:
                # Close position
                close_type = mt5.ORDER_TYPE_BUY if p.type == 1 else mt5.ORDER_TYPE_SELL
                tick = mt5.symbol_info_tick(p.symbol)
                close_price = tick.ask if p.type == 1 else tick.bid
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": p.ticket,
                    "symbol": p.symbol,
                    "volume": p.volume,
                    "type": close_type,
                    "price": close_price,
                    "deviation": 50,
                    "comment": f"SOFT_SL_{loss_pips:.0f}_pips",
                }
                
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[SOFT_SL] Closed position {ticket} at {loss_pips:.0f} pip loss")
                else:
                    print(f"[SOFT_SL] FAILED to close: retcode={result.retcode if result else 'None'}")
                break
            
            time.sleep(1)
        
        mt5.shutdown()
