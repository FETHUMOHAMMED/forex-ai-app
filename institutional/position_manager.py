import MetaTrader5 as mt5
from datetime import datetime, timezone

class PositionManager:
    """
    Manages open positions: timeout exits, breakeven stops, trailing stops.
    Called on every candle to check if positions need modification.
    """
    
    def __init__(self):
        self.max_hold_hours = 24
        self.breakeven_trigger_rr = 0.5
        self.trailing_trigger_rr = 1.0
        self.trailing_distance_pct = 0.3
        
    def manage_all(self):
        """Check all open positions and apply management rules."""
        positions = mt5.positions_get()
        if not positions:
            return []
        
        actions = []
        now = datetime.now(timezone.utc)
        
        for p in positions:
            # 1. Timeout check
            open_time = datetime.fromtimestamp(p.time, tz=timezone.utc)
            age_hours = (now - open_time).total_seconds() / 3600
            
            if age_hours > self.max_hold_hours:
                result = self._close_position(p, "TIMEOUT")
                if result:
                    actions.append("CLOSED {} #{} TIMEOUT ({:.1f}h)".format(p.symbol, p.ticket, age_hours))
                continue
            
            # 2. Non-USDJPY check
            if "USDJPY" not in p.symbol.upper():
                result = self._close_position(p, "NON_USDJPY")
                if result:
                    actions.append("CLOSED {} #{} NON-USDJPY".format(p.symbol, p.ticket))
                continue
            
            # 3. Breakeven / Trailing stop check
            tick = mt5.symbol_info_tick(p.symbol)
            if tick is None:
                continue
            
            current_price = tick.bid if p.type == 0 else tick.ask
            entry_price = p.price_open
            sl_price = p.sl
            
            if sl_price == 0:
                continue
            
            risk_distance = abs(entry_price - sl_price)
            if risk_distance == 0:
                continue
            
            if p.type == 0:
                profit_distance = current_price - entry_price
            else:
                profit_distance = entry_price - current_price
            
            profit_r = profit_distance / risk_distance if risk_distance > 0 else 0
            
            # Breakeven: move SL to entry at 0.5R
            if profit_r >= self.breakeven_trigger_rr and sl_price != entry_price:
                result = self._modify_sl(p, entry_price)
                if result:
                    actions.append("BE {} #{} SL->entry ({:.1f}R)".format(p.symbol, p.ticket, profit_r))
            
            # Trailing stop at 1R
            elif profit_r >= self.trailing_trigger_rr:
                trail_distance = profit_distance * self.trailing_distance_pct
                if p.type == 0:
                    new_sl = current_price - trail_distance
                    new_sl = self._round_to_pips(new_sl, p.symbol)
                    if new_sl > sl_price:
                        result = self._modify_sl(p, new_sl)
                        if result:
                            actions.append("TRAIL {} #{} SL={:.5f} ({:.1f}R)".format(p.symbol, p.ticket, new_sl, profit_r))
                else:
                    new_sl = current_price + trail_distance
                    new_sl = self._round_to_pips(new_sl, p.symbol)
                    if new_sl < sl_price:
                        result = self._modify_sl(p, new_sl)
                        if result:
                            actions.append("TRAIL {} #{} SL={:.5f} ({:.1f}R)".format(p.symbol, p.ticket, new_sl, profit_r))
        
        return actions
    
    def _close_position(self, position, reason):
        """Close a single position."""
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            return False
        
        price = tick.bid if position.type == 0 else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY,
            "position": position.ticket,
            "price": price,
            "deviation": 20,
            "magic": 0,
            "comment": "PM_" + reason,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE
    
    def _modify_sl(self, position, new_sl):
        """Modify stop loss of an existing position."""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": position.ticket,
            "sl": new_sl,
            "tp": position.tp,
        }
        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE
    
    def _round_to_pips(self, price, symbol):
        """Round to appropriate pip precision."""
        info = mt5.symbol_info(symbol)
        if info:
            return round(price, info.digits)
        return round(price, 5)


if __name__ == "__main__":
    mt5.initialize()
    pm = PositionManager()
    actions = pm.manage_all()
    if actions:
        for a in actions:
            print(a)
    else:
        print("No positions to manage (all clean)")
    mt5.shutdown()
