"""
GENERIC MT5 BROKER WRAPPER – works with Exness, IC Markets, etc.
Usage:
    broker = MT5Broker(account=123456, password="xxx", server="ICMarkets-Demo")
    broker.connect()
    broker.place_market_order(...)
"""

import time
import MetaTrader5 as mt5
from datetime import datetime

class MT5Broker:
    def __init__(self, account=None, password=None, server=None, auto_connect=False):
        self.account = account
        self.password = password
        self.server = server
        self.connected = False
        if auto_connect:
            self.connect()

    def connect(self):
        """Log in to the MT5 account. Can be called multiple times; will re‑login if needed."""
        # Initialize MT5 if terminal not already running
        if mt5.terminal_info() is None:
            if not mt5.initialize():
                print("❌ MT5 initialisation failed")
                return False
        # If already initialized, just proceed
        # If already connected to the same account, skip re‑login (optional)
        try:
            info = mt5.account_info()
            if info and info.login == self.account:
                self.connected = True
                return True
        except:
            pass

        result = mt5.login(self.account, password=self.password, server=self.server)
        self.connected = result
        return result

    def get_balance(self):
        if not self.connected:
            self.connect()
        info = mt5.account_info()
        return info.balance if info else 0.0

    def get_equity(self):
        if not self.connected:
            self.connect()
        info = mt5.account_info()
        return info.equity if info else 0.0

    def get_positions(self):
        """Return a list of dicts with keys: ticket, symbol, type, volume, profit, ..."""
        if not self.connected:
            self.connect()
        positions = mt5.positions_get()
        result = []
        if positions:
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': pos.type,          # 0=BUY, 1=SELL
                    'volume': pos.volume,
                    'profit': pos.profit,
                    'open_price': pos.price_open,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'time': pos.time, 
                })
        return result

    def place_market_order(self, symbol, order_type, entry, sl, tp, confidence, volume=0.01):
        """
        Place a market order with broker‑aware filling and full retry logic.
        Returns a dict with 'ticket' on success, or None on failure.
        """
        import time
        MAX_RETRIES = 3
        RETRY_DELAY = 2  # seconds

        # Ensure the symbol is selected in Market Watch
        if not mt5.symbol_select(symbol, True):
            print(f"⚠️ {symbol} – symbol_select failed, symbol may not be available")
            return None

        # --- Fetch supported filling modes once ---
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"⚠️ {symbol} – symbol_info not available")
            return None

        # Determine the correct filling mode
        filling_modes = symbol_info.filling_mode
        if filling_modes & 1:           # SYMBOL_FILLING_FOK
            fill_type = mt5.ORDER_FILLING_FOK
        elif filling_modes & 2:         # SYMBOL_FILLING_IOC
            fill_type = mt5.ORDER_FILLING_IOC
        else:
            fill_type = mt5.ORDER_FILLING_RETURN

        # --- Adaptive deviation (point‑based) ---
        point = symbol_info.point if symbol_info.point else 0.00001
        if symbol in ('XAUUSD', 'XAGUSD'):
            deviation = 100
        elif 'JPY' in symbol:
            deviation = 20
        elif symbol in ('USDSEK', 'USDMXN', 'USDZAR', 'USDBRL', 'EURTRY', 'GBPZAR', 'USDPLN', 'USDCLP'):
            deviation = 50
        else:
            deviation = 30   # major forex (3 pips)

        for attempt in range(1, MAX_RETRIES + 1):
            # Ensure we are connected
            if not self.connected:
                self.connect()
            if not self.connected:
                print(f"⚠️ {symbol} – not connected, aborting order")
                return None

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                print(f"⚠️ {symbol} tick unavailable – attempt {attempt}/{MAX_RETRIES}")
                time.sleep(RETRY_DELAY)
                continue

            if order_type == 'BUY':
                request_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                request_type = mt5.ORDER_TYPE_SELL
                price = tick.bid

            # ---- Margin check ----
            if not self._check_margin(symbol, order_type, volume, price):
                print(f"💰 {symbol} – insufficient margin (vol={volume})")
                return None

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": request_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": deviation,          # <-- deviation now included
                "magic": 234000,
                "comment": f"AI_trade_conf{confidence:.2f}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": fill_type,
            }

            result = mt5.order_send(request)
            print(f"[MT5 ORDER] {symbol} retcode={result.retcode if result else 'None'} comment={result.comment if result else 'N/A'} order={result.order if result else 'N/A'}")
            if result is None:
                print(f"⚠️ {symbol} – order_send returned None (attempt {attempt})")
                time.sleep(RETRY_DELAY)
                continue

            retcode = result.retcode
            if retcode == mt5.TRADE_RETCODE_DONE:
                # Retrieve the actual position ticket
                positions = mt5.positions_get(symbol=symbol)
                if positions:
                    ticket = max(p.ticket for p in positions)
                else:
                    ticket = result.order
                return {'ticket': ticket}
            # Transient errors – retry
            elif retcode in (10004,   # REQUOTE
                             10006,   # OFF_QUOTES
                             10013):  # TRADE_CONTEXT_BUSY
                print(f"🔄 {symbol} – retrying after code {retcode} (attempt {attempt})")
                time.sleep(RETRY_DELAY)
                continue
            # Permanent errors – stop immediately
            elif retcode == mt5.TRADE_RETCODE_NO_MONEY:
                print(f"💰 {symbol} – no money (code {retcode})")
                return None
            elif retcode == mt5.TRADE_RETCODE_MARKET_CLOSED:
                print(f"🌙 {symbol} – market closed")
                return None
            elif retcode == mt5.TRADE_RETCODE_INVALID_STOPS:
                print(f"📏 {symbol} – invalid stops (SL/TP too close?)")
                return None
            else:
                # Unknown error – log details and retry once
                print(f"Order failed: code={result.retcode} comment={result.comment} mt5_error={mt5.last_error()}")
                if attempt == MAX_RETRIES:
                    return None
                self.connect()
                time.sleep(RETRY_DELAY)
                continue

        return None

    def _check_margin(self, symbol, order_type, volume, price):
        """Return True if there is enough margin for this trade, False otherwise."""
        try:
            if order_type == 'BUY':
                trade_type = mt5.ORDER_TYPE_BUY
            else:
                trade_type = mt5.ORDER_TYPE_SELL
            margin = mt5.order_calc_margin(trade_type, symbol, volume, price)
            if margin is None:
                return False
            account = mt5.account_info()
            if account is None:
                return False
            return account.margin_free >= margin
        except:
            return False
        
    def shutdown(self):
        mt5.shutdown()
        self.connected = False