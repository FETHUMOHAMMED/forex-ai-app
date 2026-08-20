"""
Phase 9: Event Bus - Decoupled trade lifecycle events.
Modules subscribe to events they care about. No direct calls.
Signal -> Decision -> Execution -> Exit -> Analysis. All tracked.
"""
import sys, os, json, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone
from typing import Callable, Dict, List
from dataclasses import dataclass, field, asdict

# ============================================
# EVENT TYPES
# ============================================
@dataclass
class TradeEvent:
    """Base trade event - all events inherit from this"""
    pair: str
    event_type: str = "GENERIC"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class SignalGenerated(TradeEvent):
    """A signal was produced by the pipeline"""
    direction: str = "NONE"
    confidence: float = 0.0
    institutional_score: float = 0.0
    passed_filters: bool = False
    rejection_reason: str = ""
    event_type: str = "SIGNAL_GENERATED"

@dataclass
class SignalRejected(TradeEvent):
    """A signal was rejected by filters"""
    direction: str = "NONE"
    reason: str = ""
    filter_name: str = ""
    event_type: str = "SIGNAL_REJECTED"

@dataclass
class TradeExecuted(TradeEvent):
    """A trade was sent to the broker"""
    direction: str = ""
    entry: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    volume: float = 0.0
    ticket: int = 0
    event_type: str = "TRADE_EXECUTED"

@dataclass
class TradeClosed(TradeEvent):
    """A trade was closed"""
    direction: str = ""
    entry: float = 0.0
    exit_price: float = 0.0
    pnl: float = 0.0
    result: str = ""  # WIN or LOSS
    event_type: str = "TRADE_CLOSED"

@dataclass
class AccountPaused(TradeEvent):
    """Account was paused (circuit breaker)"""
    reason: str = ""
    pause_hours: int = 24
    event_type: str = "ACCOUNT_PAUSED"

@dataclass
class DailyReset(TradeEvent):
    """Daily counters reset"""
    event_type: str = "DAILY_RESET"


# ============================================
# EVENT BUS
# ============================================
class EventBus:
    """
    Publish-subscribe event bus for trade lifecycle.
    Modules subscribe to events they care about.
    Database logger is a built-in subscriber.
    """
    
    def __init__(self, db_path: str = "ai-service/trades.db"):
        self._subscribers: Dict[str, List[Callable]] = {}
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create event log table"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trade_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            pair TEXT,
            data TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )''')
        conn.commit()
        conn.close()
    
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def publish(self, event: TradeEvent):
        """Publish an event to all subscribers and log to database."""
        # Log to database
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''INSERT INTO trade_events (timestamp, event_type, pair, data)
                        VALUES (?, ?, ?, ?)''',
                     (event.timestamp, event.event_type, event.pair, json.dumps(asdict(event))))
            conn.commit()
            conn.close()
        except Exception:
            pass
        
        # Notify subscribers
        event_type = event.event_type
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"[EVENT BUS] Subscriber error: {e}")
    
    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        """Get recent events from the log"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT timestamp, event_type, pair, data FROM trade_events 
                     ORDER BY id DESC LIMIT ?''', (limit,))
        rows = [{'timestamp': r[0], 'event_type': r[1], 'pair': r[2], 'data': json.loads(r[3]) if r[3] else {}} 
                for r in c.fetchall()]
        conn.close()
        return rows
    
    def get_stats(self) -> Dict:
        """Get event statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT event_type, COUNT(*) FROM trade_events GROUP BY event_type''')
        stats = {r[0]: r[1] for r in c.fetchall()}
        conn.close()
        return stats


# ============================================
# BUILT-IN SUBSCRIBERS
# ============================================
class PerformanceTracker:
    """Tracks P&L from trade events"""
    
    def __init__(self):
        self.total_pnl = 0.0
        self.wins = 0
        self.losses = 0
    
    def on_trade_closed(self, event: TradeClosed):
        self.total_pnl += event.pnl
        if event.pnl > 0:
            self.wins += 1
        else:
            self.losses += 1
    
    def stats(self) -> Dict:
        total = self.wins + self.losses
        return {
            'total_trades': total,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': round(self.wins/total*100, 1) if total > 0 else 0,
            'total_pnl': round(self.total_pnl, 2),
        }


class AlertSystem:
    """Sends alerts on critical events"""
    
    def on_account_paused(self, event: AccountPaused):
        print(f"[ALERT] ACCOUNT PAUSED: {event.reason} for {event.pause_hours}h")
    
    def on_trade_closed(self, event: TradeClosed):
        if event.pnl < -50:
            print(f"[ALERT] LARGE LOSS: {event.pair} ${event.pnl:.2f}")


# ============================================
# SINGLETON
# ============================================
# Global event bus instance
bus = EventBus()
tracker = PerformanceTracker()
alerts = AlertSystem()

# Register built-in subscribers
bus.subscribe('TRADE_CLOSED', tracker.on_trade_closed)
bus.subscribe('TRADE_CLOSED', alerts.on_trade_closed)
bus.subscribe('ACCOUNT_PAUSED', alerts.on_account_paused)


if __name__ == '__main__':
    # Test the event bus
    print("=== Event Bus Test ===\n")
    
    # Simulate a trade lifecycle
    signal = SignalGenerated(pair='EURUSD', direction='SELL', confidence=0.55, 
                             institutional_score=68, passed_filters=True)
    bus.publish(signal)
    print(f"[SIGNAL] {signal.pair} {signal.direction} conf={signal.confidence}")
    
    reject = SignalRejected(pair='GBPUSD', direction='BUY', reason='Inst score 47 < 55', filter_name='institutional')
    bus.publish(reject)
    print(f"[REJECT] {reject.pair}: {reject.reason}")
    
    execute = TradeExecuted(pair='EURUSD', direction='SELL', entry=1.1050, 
                            stop_loss=1.1080, take_profit=1.0990, volume=0.01, ticket=12345)
    bus.publish(execute)
    print(f"[EXECUTE] {execute.pair} ticket={execute.ticket}")
    
    close_win = TradeClosed(pair='EURUSD', direction='SELL', entry=1.1050, 
                            exit_price=1.0990, pnl=60.0, result='WIN')
    bus.publish(close_win)
    print(f"[CLOSE] {close_win.pair} PnL=${close_win.pnl:.2f} {close_win.result}")
    
    close_loss = TradeClosed(pair='GBPUSD', direction='BUY', entry=1.3050, 
                             exit_price=1.3020, pnl=-30.0, result='LOSS')
    bus.publish(close_loss)
    print(f"[CLOSE] {close_loss.pair} PnL=${close_loss.pnl:.2f} {close_loss.result}")
    
    print(f"\nTracker stats: {tracker.stats()}")
    print(f"Event stats: {bus.get_stats()}")
    print(f"\nRecent events: {len(bus.get_recent_events())}")
