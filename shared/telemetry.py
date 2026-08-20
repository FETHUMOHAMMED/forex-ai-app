"""
Phase 10: Production Telemetry - Track everything.
Every trade, every decision, every filter result.
This becomes your training dataset for Volume 10+.
"""
import sys, os, json, sqlite3, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from shared.event_bus import bus, TradeEvent, SignalGenerated, TradeExecuted, TradeClosed


@dataclass
class TradeRecord:
    """Complete trade record - everything we know about one trade."""
    # Identification
    trade_id: str = ""
    pair: str = ""
    direction: str = ""
    timestamp: str = ""
    
    # Signal
    confidence: float = 0.0
    institutional_score: float = 0.0
    institutional_bias: str = "NEUTRAL"
    dealer_pressure: str = "NEUTRAL"
    liquidity_state: str = "NO_EVENT"
    regime: str = "UNKNOWN"
    session: str = "UNKNOWN"
    
    # Execution
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    volume: float = 0.0
    spread: float = 0.0
    slippage: float = 0.0
    execution_latency_ms: float = 0.0
    
    # Filters passed
    filters_passed: List[str] = field(default_factory=list)
    
    # Outcome
    exit_price: float = 0.0
    pnl: float = 0.0
    pnl_pips: float = 0.0
    result: str = "PENDING"
    r_multiple: float = 0.0
    holding_time_minutes: float = 0.0
    max_favorable: float = 0.0
    max_adverse: float = 0.0


class Telemetry:
    """
    Production telemetry system.
    Records every trade with full context for future ML training.
    """
    
    def __init__(self, db_path: str = "ai-service/trades.db"):
        self.db_path = db_path
        self._init_db()
        self._subscribe()
        self._pending: Dict[str, TradeRecord] = {}
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trade_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT UNIQUE,
            timestamp TEXT,
            pair TEXT, direction TEXT, session TEXT,
            confidence REAL, institutional_score REAL, institutional_bias TEXT,
            dealer_pressure TEXT, liquidity_state TEXT, regime TEXT,
            entry_price REAL, stop_loss REAL, take_profit REAL, volume REAL,
            spread REAL, slippage REAL, execution_latency_ms REAL,
            filters_passed TEXT,
            exit_price REAL, pnl REAL, pnl_pips REAL, result TEXT,
            r_multiple REAL, holding_time_minutes REAL,
            max_favorable REAL, max_adverse REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )''')
        conn.commit()
        conn.close()
    
    def _subscribe(self):
        """Subscribe to event bus for automatic tracking"""
        bus.subscribe('TRADE_EXECUTED', self._on_executed)
        bus.subscribe('TRADE_CLOSED', self._on_closed)
    
    def _on_executed(self, event: TradeExecuted):
        """Track when a trade is opened"""
        trade_id = f"{event.pair}_{event.ticket}_{int(time.time())}"
        record = TradeRecord(
            trade_id=trade_id,
            pair=event.pair,
            direction=event.direction,
            timestamp=event.timestamp,
            entry_price=event.entry,
            stop_loss=event.stop_loss,
            take_profit=event.take_profit,
            volume=event.volume,
        )
        self._pending[trade_id] = record
    
    def _on_closed(self, event: TradeClosed):
        """Track when a trade closes - complete the record"""
        # Find matching pending record
        record = None
        for tid, rec in self._pending.items():
            if rec.pair == event.pair and rec.direction == event.direction:
                record = rec
                del self._pending[tid]
                break
        
        if record is None:
            record = TradeRecord(
                trade_id=f"{event.pair}_manual_{int(time.time())}",
                pair=event.pair,
                direction=event.direction,
                entry_price=event.entry,
            )
        
        # Fill in outcome
        record.exit_price = event.exit_price
        record.pnl = event.pnl
        record.result = event.result
        
        if record.entry_price > 0:
            if record.direction == 'BUY':
                record.pnl_pips = (event.exit_price - record.entry_price) / record.entry_price * 10000
            else:
                record.pnl_pips = (record.entry_price - event.exit_price) / record.entry_price * 10000
            
            risk = abs(record.entry_price - record.stop_loss) if record.stop_loss > 0 else record.entry_price * 0.002
            record.r_multiple = record.pnl / (risk * 100000 * (record.volume or 0.01)) if risk > 0 and record.volume else 0
        
        # Save to database
        self._save(record)
    
    def _save(self, record: TradeRecord):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO trade_telemetry
            (trade_id, timestamp, pair, direction, session,
             confidence, institutional_score, institutional_bias,
             dealer_pressure, liquidity_state, regime,
             entry_price, stop_loss, take_profit, volume,
             spread, slippage, execution_latency_ms,
             filters_passed,
             exit_price, pnl, pnl_pips, result,
             r_multiple, holding_time_minutes,
             max_favorable, max_adverse)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (record.trade_id, record.timestamp, record.pair, record.direction, record.session,
             record.confidence, record.institutional_score, record.institutional_bias,
             record.dealer_pressure, record.liquidity_state, record.regime,
             record.entry_price, record.stop_loss, record.take_profit, record.volume,
             record.spread, record.slippage, record.execution_latency_ms,
             json.dumps(record.filters_passed),
             record.exit_price, record.pnl, record.pnl_pips, record.result,
             record.r_multiple, record.holding_time_minutes,
             record.max_favorable, record.max_adverse))
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """Get aggregated telemetry stats"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT COUNT(*), SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),
                     ROUND(AVG(pnl),2), ROUND(SUM(pnl),2),
                     ROUND(AVG(CASE WHEN result='WIN' THEN r_multiple END),2),
                     ROUND(AVG(CASE WHEN result='LOSS' THEN r_multiple END),2)
                     FROM trade_telemetry WHERE result IN ('WIN','LOSS')''')
        r = c.fetchone()
        conn.close()
        total, wins, avg_pnl, net, avg_r_win, avg_r_loss = r
        return {
            'total_trades': total or 0,
            'wins': wins or 0,
            'losses': (total or 0) - (wins or 0),
            'win_rate': round(wins/(total)*100,1) if total else 0,
            'avg_pnl': avg_pnl or 0,
            'net_pnl': net or 0,
            'avg_r_win': avg_r_win or 0,
            'avg_r_loss': avg_r_loss or 0,
        }
    
    def export_training_data(self, min_trades: int = 50) -> Optional[str]:
        """Export telemetry as ML training dataset (JSON)"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM trade_telemetry WHERE result IN ("WIN","LOSS")')
        count = c.fetchone()[0]
        
        if count < min_trades:
            conn.close()
            return None
        
        c.execute('''SELECT * FROM trade_telemetry WHERE result IN ("WIN","LOSS") ORDER BY id''')
        columns = [desc[0] for desc in c.description]
        rows = [dict(zip(columns, r)) for r in c.fetchall()]
        conn.close()
        
        path = f'ai-service/training_data_{datetime.now(timezone.utc).strftime("%Y%m%d")}.json'
        with open(path, 'w') as f:
            json.dump({'count': len(rows), 'trades': rows}, f, indent=2)
        return path


# Singleton
telemetry = Telemetry()


if __name__ == '__main__':
    print("=== Telemetry Test ===\n")
    
    # Simulate a complete trade lifecycle through event bus
    exec_evt = TradeExecuted(pair='EURUSD', direction='SELL', entry=1.1050,
                             stop_loss=1.1080, take_profit=1.0990, volume=0.01, ticket=99999)
    bus.publish(exec_evt)
    print(f"[OPEN] EURUSD SELL @ 1.1050")
    
    close_evt = TradeClosed(pair='EURUSD', direction='SELL', entry=1.1050,
                            exit_price=1.0990, pnl=60.0, result='WIN')
    bus.publish(close_evt)
    print(f"[CLOSE] PnL=+60.00 WIN")
    
    print(f"\nTelemetry stats: {telemetry.get_stats()}")
    print(f"Training data export: {telemetry.export_training_data(min_trades=1)}")
