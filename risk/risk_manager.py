# risk_manager.py
import MetaTrader5 as mt5
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

MAX_OPEN_TRADES = 5
USD_CORRELATED = {'EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD'}
MAX_TRADE_DURATION_HOURS = 12

def get_open_positions():
    """
    Return a list of dicts with keys: 'pair', 'type' (0=BUY, 1=SELL).
    Uses MT5 to fetch current positions.
    """
    positions = mt5.positions_get()
    if positions is None:
        return []
    result = []
    for p in positions:
        result.append({'pair': p.symbol, 'type': p.type, 'ticket': p.ticket})
    return result

def should_skip_due_to_risk(signal_pair, signal_direction, open_positions=None):
    """
    Return True if the trade should be skipped for risk reasons.
    signal_direction: 'BUY' or 'SELL'.
    """
    if open_positions is None:
        open_positions = get_open_positions()

    # a) Max concurrent trades
    if len(open_positions) >= MAX_OPEN_TRADES:
        logger.info("❌ Max open trades reached (%d)", MAX_OPEN_TRADES)
        return True

    # b) Correlation filter
    if signal_pair in USD_CORRELATED:
        same_direction_count = 0
        for pos in open_positions:
            if pos['pair'] in USD_CORRELATED:
                pos_dir = 'BUY' if pos['type'] == 0 else 'SELL'
                if pos_dir == signal_direction:
                    same_direction_count += 1
        if same_direction_count >= 3:
            logger.info("❌ Correlation limit: %d USD positions already %s", same_direction_count, signal_direction)
            return True

    return False

def close_order(mt5_position):
    """
    Close a single MT5 position (dict with 'pair', 'type', 'ticket').
    """
    symbol = mt5_position['pair']
    ticket = mt5_position['ticket']
    order_type = mt5_position['type']  # 0=BUY, 1=SELL

    # To close a BUY position, we must SELL the same volume.
    # We'll use mt5.Close.
    # Note: mt5.Close might close by ticket and volume; we'll use the position's volume.
    pos_info = mt5.positions_get(ticket=ticket)
    if pos_info is None or len(pos_info) == 0:
        return
    volume = pos_info[0].volume
    price = mt5.symbol_info_tick(symbol).bid if order_type == 0 else mt5.symbol_info_tick(symbol).ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_SELL if order_type == 0 else mt5.ORDER_TYPE_BUY,
        "position": ticket,
        "price": price,
        "deviation": 10,
        "comment": "time exit",
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error("Failed to close %s: %s", symbol, result.comment)
    else:
        logger.info("⏰ Closed %s due to time exit", symbol)

def close_expired_trades():
    """Close any open position held for more than MAX_TRADE_DURATION_HOURS hours."""
    positions = mt5.positions_get()
    if positions is None:
        return
    now = datetime.now()
    for pos in positions:
        open_time = datetime.fromtimestamp(pos.time)
        age_hours = (now - open_time).total_seconds() / 3600
        if age_hours >= MAX_TRADE_DURATION_HOURS:
            logger.info(f"⏰ {pos.symbol} held for {age_hours:.1f}h – closing")
            close_order({'pair': pos.symbol, 'type': pos.type, 'ticket': pos.ticket})