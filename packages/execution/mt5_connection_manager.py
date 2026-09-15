"""MT5 CONNECTION MANAGER - Persistent terminal session."""
import MetaTrader5 as mt5
import threading
import time
from datetime import datetime, timezone

class MT5ConnectionManager:
    """
    Manages a SINGLE persistent MT5 connection.
    Avoids repeated initialize/shutdown.
    Thread-safe for execution boundary.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
                cls._instance._lock = threading.Lock()
        return cls._instance
    
    def connect(self) -> bool:
        """Establish persistent MT5 connection."""
        with self._lock:
            if self._initialized:
                # Check if still alive
                try:
                    account = mt5.account_info()
                    if account:
                        return True
                except:
                    pass
                self._initialized = False
            
            # Fresh connection
            if not mt5.initialize():
                self._initialized = False
                return False
            
            self._initialized = True
            self._connected_at = datetime.now(timezone.utc).isoformat()
            return True
    
    def disconnect(self):
        """Shutdown MT5 connection (call at program end)."""
        with self._lock:
            if self._initialized:
                mt5.shutdown()
                self._initialized = False
    
    def is_connected(self) -> bool:
        """Check if MT5 is connected."""
        with self._lock:
            if not self._initialized:
                return False
            try:
                account = mt5.account_info()
                return account is not None
            except:
                return False
    
    def get_symbol_info(self, symbol: str):
        """Get symbol info through persistent connection."""
        if not self.connect():
            return None
        return mt5.symbol_info(symbol)
    
    def get_symbol_tick(self, symbol: str):
        """Get current tick through persistent connection."""
        if not self.connect():
            return None
        return mt5.symbol_info_tick(symbol)
    
    def get_positions(self):
        """Get open positions through persistent connection."""
        if not self.connect():
            return None
        return mt5.positions_get()

# Global singleton
mt5_manager = MT5ConnectionManager()

if __name__ == "__main__":
    print("="*70)
    print("  MT5 CONNECTION MANAGER TEST")
    print("="*70)
    
    # Connect once
    print("\n  Connecting...")
    ok = mt5_manager.connect()
    print(f"  Connected: {ok}")
    
    if ok:
        # Use the SAME connection multiple times
        print("\n  Using persistent connection:")
        for i in range(3):
            tick = mt5_manager.get_symbol_tick("USDJPYm")
            if tick:
                print(f"    Request {i+1}: bid={tick.bid:.3f}")
            else:
                print(f"    Request {i+1}: failed")
        
        print(f"\n  Still connected after 3 requests: {mt5_manager.is_connected()}")
        print(f"  Connected at: {mt5_manager._connected_at}")
        
        # DON'T disconnect - let it persist
        print("\n  Connection remains OPEN for future use")
        print("  Call disconnect() only at program shutdown")

