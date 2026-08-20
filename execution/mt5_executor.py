"""
Execution Layer - The ONE place trades are sent to MT5.
Pure execution logic. No signals, no analysis, no decisions.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import MetaTrader5 as mt5
from datetime import datetime, timezone
from typing import Optional, Dict, List
from shared.trade_signal import TradeSignal


class MT5Executor:
    """
    Executes trades on MT5. Single responsibility: send orders.
    Does NOT decide what to trade. Only executes what it's told.
    """
    
    def __init__(self, account: int, password: str, server: str):
        self.account = account
        self.password = password
        self.server = server
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to MT5 account"""
        if not mt5.initialize():
            return False
        self.connected = mt5.login(self.account, password=self.password, server=self.server)
        return self.connected
    
    def disconnect(self):
        mt5.shutdown()
        self.connected = False
    
    def execute(self, signal: TradeSignal, risk_percent: float = 0.05) -> Dict:
        """
        Execute a trade signal.
        
        Args:
            signal: Validated TradeSignal
            risk_percent: Risk per trade (0-100)
            
        Returns:
            Dict with execution result
        """
        if not signal.is_valid:
            return {'success': False, 'error': 'Signal is not valid: ' + signal.rejection_reason}
        
        if not self.connected:
            return {'success': False, 'error': 'Not connected to MT5'}
        
        symbol = signal.pair + 'm'
        mt5.symbol_select(symbol, True)
        
        # Get account info for position sizing
        account_info = mt5.account_info()
        if not account_info:
            return {'success': False, 'error': 'Cannot get account info'}
        
        balance = account_info.balance
        
        # Calculate position size
        risk_amount = balance * risk_percent / 100
        sl_distance = abs(signal.entry - signal.stop_loss)
        if sl_distance == 0:
            return {'success': False, 'error': 'Zero stop distance'}
        
        # Get symbol info for volume step
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return {'success': False, 'error': f'Cannot get symbol info for {symbol}'}
        
        # Calculate lot size
        pip_value = 100000  # Standard lot
        lot_size = risk_amount / (sl_distance * pip_value)
        lot_size = round(lot_size, 2)
        lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
        
        # Prepare order
        order_type = mt5.ORDER_TYPE_BUY if signal.direction == 'BUY' else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).ask if signal.direction == 'BUY' else mt5.symbol_info_tick(symbol).bid
        
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': lot_size,
            'type': order_type,
            'price': price,
            'sl': signal.stop_loss,
            'tp': signal.take_profit,
            'deviation': 20,
            'magic': 0,
            'comment': f'AI_{signal.direction}_conf{signal.confidence:.1f}',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            return {
                'success': True,
                'ticket': result.order,
                'volume': lot_size,
                'price': result.price,
                'entry': signal.entry,
                'sl': signal.stop_loss,
                'tp': signal.take_profit,
                'pair': signal.pair,
                'direction': signal.direction,
            }
        else:
            return {
                'success': False,
                'error': f'MT5 retcode={result.retcode} comment={result.comment}',
                'retcode': result.retcode,
            }
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        if not self.connected:
            return []
        positions = mt5.positions_get()
        if not positions:
            return []
        return [{
            'ticket': p.ticket,
            'symbol': p.symbol.replace('m', ''),
            'type': 'BUY' if p.type == 0 else 'SELL',
            'volume': p.volume,
            'entry': p.price_open,
            'sl': p.sl,
            'tp': p.tp,
            'profit': p.profit,
            'open_time': datetime.fromtimestamp(p.time, tz=timezone.utc).isoformat(),
        } for p in positions]
    
    def close_position(self, ticket: int) -> Dict:
        """Close a specific position by ticket"""
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {'success': False, 'error': 'Position not found'}
        position = position[0]
        
        symbol = position.symbol
        order_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if position.type == 0 else mt5.symbol_info_tick(symbol).ask
        
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': position.volume,
            'type': order_type,
            'position': ticket,
            'price': price,
            'deviation': 20,
            'magic': 0,
            'comment': 'AI_close',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        return {
            'success': result.retcode == mt5.TRADE_RETCODE_DONE,
            'ticket': ticket,
            'price': result.price if result else 0,
        }


# Quick test
if __name__ == '__main__':
    import json, os
    config_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'config.json')
    with open(config_path) as f:
        config = json.load(f)
    
    demo2 = [a for a in config['accounts'] if a['name'] == 'Demo2'][0]
    executor = MT5Executor(demo2['account'], os.getenv('EXNESS_DEMO2_PASSWORD', ''), demo2['server'])
    
    if executor.connect():
        print(f"Connected to {demo2['server']}")
        positions = executor.get_positions()
        print(f"Open positions: {len(positions)}")
        for p in positions:
            print(f"  {p['symbol']} {p['type']} @ {p['entry']} PnL={p['profit']:.2f}")
        executor.disconnect()
    else:
        print("Connection failed - MT5 may not be running")
