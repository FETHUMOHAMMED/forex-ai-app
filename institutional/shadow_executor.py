"""
Volume 9.8: Shadow Executor
Simulates trade outcomes for every AI decision.
Generates labeled training data without risking money.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict

class ShadowExecutor:
    """Simulates trade execution and tracks outcomes"""
    
    def __init__(self):
        self.db_path = "ai-service/trades.db"
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS shadow_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            pair TEXT NOT NULL,
            signal TEXT NOT NULL,
            confidence REAL,
            regime TEXT,
            grade TEXT,
            quality_score REAL,
            entry_price REAL,
            stop_loss REAL,
            take_profit REAL,
            exit_price REAL,
            pnl_pips REAL,
            r_multiple REAL,
            result TEXT,
            bars_to_exit INTEGER,
            max_favorable REAL,
            max_adverse REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )''')
        conn.commit()
        conn.close()
    
    def execute_shadow(self, signal_dict: Dict, regime: str, grade: str, quality_score: float, 
                       hold_bars: int = 20) -> Dict:
        """Simulate a trade and track outcome"""
        pair = signal_dict.get('pair', 'UNKNOWN')
        signal = signal_dict.get('signal', 'UNKNOWN')
        confidence = signal_dict.get('confidence', 0.5)
        entry = signal_dict.get('entry', 0)
        
        if entry == 0:
            return None
        
        # Calculate SL/TP
        if signal == 'BUY':
            sl = entry * 0.998
            tp = entry * 1.004
        else:
            sl = entry * 1.002
            tp = entry * 0.996
        
        # Get forward data
        symbol = pair + 'm'
        mt5.symbol_select(symbol, True)
        now = datetime.now(timezone.utc)
        end = now + timedelta(hours=hold_bars)
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, now, end)
        
        if rates is None or len(rates) < 2:
            return None
        
        df = pd.DataFrame(rates)
        
        # Simulate outcome
        exit_price = entry
        result = "OPEN"
        bars = 0
        max_fav = 0
        max_adv = 0
        
        for i in range(len(df)):
            high = float(df['high'].iloc[i])
            low = float(df['low'].iloc[i])
            bars = i + 1
            
            if signal == 'BUY':
                max_fav = max(max_fav, (high - entry) / entry * 10000)
                max_adv = max(max_adv, (entry - low) / entry * 10000)
                if high >= tp:
                    exit_price = tp
                    result = "TP_HIT"
                    break
                elif low <= sl:
                    exit_price = sl
                    result = "SL_HIT"
                    break
            else:
                max_fav = max(max_fav, (entry - low) / entry * 10000)
                max_adv = max(max_adv, (high - entry) / entry * 10000)
                if low <= tp:
                    exit_price = tp
                    result = "TP_HIT"
                    break
                elif high >= sl:
                    exit_price = sl
                    result = "SL_HIT"
                    break
        
        if result == "OPEN":
            exit_price = float(df['close'].iloc[-1])
            pnl = (exit_price - entry) / entry * 10000 if signal == 'BUY' else (entry - exit_price) / entry * 10000
            result = "PROFIT" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
        
        # Calculate metrics
        pnl_pips = (exit_price - entry) / entry * 10000 if signal == 'BUY' else (entry - exit_price) / entry * 10000
        risk = abs(entry - sl) / entry * 10000
        r_multiple = round(pnl_pips / risk, 2) if risk > 0 else 0
        
        # Save
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        c.execute('''INSERT INTO shadow_executions
            (timestamp, pair, signal, confidence, regime, grade, quality_score,
             entry_price, stop_loss, take_profit, exit_price, pnl_pips, r_multiple,
             result, bars_to_exit, max_favorable, max_adverse)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (now_iso, pair, signal, confidence, regime, grade, quality_score,
             entry, sl, tp, exit_price, round(pnl_pips, 1), r_multiple,
             result, bars, round(max_fav, 1), round(max_adv, 1)))
        conn.commit()
        conn.close()
        
        return {
            'pair': pair, 'signal': signal, 'result': result,
            'pnl_pips': round(pnl_pips, 1), 'r_multiple': r_multiple,
            'bars': bars, 'max_fav': round(max_fav, 1), 'max_adv': round(max_adv, 1)
        }
    
    def stats(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*), result FROM shadow_executions GROUP BY result")
        print("Shadow Executions:")
        for row in c.fetchall():
            print(f"  {row[1]}: {row[0]}")
        c.execute("SELECT COUNT(*) FROM shadow_executions")
        total = c.fetchone()[0]
        c.execute("SELECT AVG(r_multiple) FROM shadow_executions WHERE result IN ('TP_HIT','PROFIT')")
        avg_win = c.fetchone()[0]
        c.execute("SELECT AVG(r_multiple) FROM shadow_executions WHERE result IN ('SL_HIT','LOSS')")
        avg_loss = c.fetchone()[0]
        print(f"  Total: {total}")
        print(f"  Avg win R: {round(avg_win, 2) if avg_win else 'N/A'}")
        print(f"  Avg loss R: {round(avg_loss, 2) if avg_loss else 'N/A'}")
        conn.close()


if __name__ == "__main__":
    mt5.initialize()
    se = ShadowExecutor()
    
    # Test with current market
    from institutional.market_microstructure import MarketMicrostructure
    import pandas as pd
    
    for pair in ['USDJPY', 'NZDUSD', 'EURUSD']:
        symbol = pair + 'm'
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
        if rates is not None:
            df = pd.DataFrame(rates)
            current = float(df['close'].iloc[-1])
            signal = {'pair': pair, 'signal': 'BUY', 'confidence': 0.52, 'entry': current}
            result = se.execute_shadow(signal, 'RANGING', 'B', 55)
            if result:
                print(f"{pair}: {result['result']} | {result['pnl_pips']} pips | {result['r_multiple']}R")
    
    se.stats()
    mt5.shutdown()
