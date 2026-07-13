"""
Volume 9.7: Decision Outcome Tracker
Tracks what happens AFTER each research decision.
Answers: "Did this Grade A BUY actually work out?"
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List

class OutcomeTracker:
    """Tracks forward outcomes for research decisions"""
    
    def __init__(self):
        self.db_path = "ai-service/trades.db"
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Add outcome columns to research_decisions
        try:
            c.execute("ALTER TABLE research_decisions ADD COLUMN outcome_price REAL")
        except: pass
        try:
            c.execute("ALTER TABLE research_decisions ADD COLUMN outcome_pnl_pips REAL")
        except: pass
        try:
            c.execute("ALTER TABLE research_decisions ADD COLUMN outcome_result TEXT")
        except: pass
        try:
            c.execute("ALTER TABLE research_decisions ADD COLUMN outcome_checked TEXT")
        except: pass
        
        conn.commit()
        conn.close()
    
    def track_outcomes(self, minutes_forward: int = 60):
        """Check what happened to all untracked decisions after N minutes"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""SELECT id, pair, signal, timestamp FROM research_decisions 
                     WHERE outcome_result IS NULL ORDER BY id""")
        pending = c.fetchall()
        
        if not pending:
            print("No pending outcomes to track")
            conn.close()
            return 0
        
        mt5.initialize()
        tracked = 0
        now = datetime.now(timezone.utc)
        
        for row in pending:
            decision_id, pair, signal, ts = row
            try:
                decision_time = datetime.fromisoformat(ts)
                if decision_time.tzinfo is None:
                    decision_time = decision_time.replace(tzinfo=timezone.utc)
                
                # Only check if enough time has passed
                if (now - decision_time).total_seconds() < minutes_forward * 60:
                    continue
                
                # Get price at decision time and current price
                symbol = pair + 'm'
                mt5.symbol_select(symbol, True)
                
                # Get rates around decision time
                end_time = decision_time + timedelta(minutes=minutes_forward)
                rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, decision_time, end_time)
                
                if rates is None or len(rates) < 2:
                    continue
                
                entry_price = rates[0][1]  # open of first candle
                
                # Check if TP or SL would have been hit
                if signal == 'BUY':
                    high = max(r[2] for r in rates)  # highest high
                    low = min(r[3] for r in rates)    # lowest low
                    tp_hit = high >= entry_price * 1.002
                    sl_hit = low <= entry_price * 0.998
                    final_price = rates[-1][4]  # close of last candle
                    pnl_pips = (final_price - entry_price) / entry_price * 10000
                else:  # SELL
                    high = max(r[2] for r in rates)
                    low = min(r[3] for r in rates)
                    tp_hit = low <= entry_price * 0.998
                    sl_hit = high >= entry_price * 1.002
                    final_price = rates[-1][4]
                    pnl_pips = (entry_price - final_price) / entry_price * 10000
                
                if tp_hit:
                    result = "TP_HIT"
                elif sl_hit:
                    result = "SL_HIT"
                elif pnl_pips > 0:
                    result = "PROFIT"
                elif pnl_pips < 0:
                    result = "LOSS"
                else:
                    result = "BREAKEVEN"
                
                c.execute("""UPDATE research_decisions SET 
                    outcome_price=?, outcome_pnl_pips=?, outcome_result=?, outcome_checked=?
                    WHERE id=?""", (final_price, round(pnl_pips, 1), result, now.isoformat(), decision_id))
                tracked += 1
                
            except Exception as e:
                pass
        
        conn.commit()
        conn.close()
        mt5.shutdown()
        return tracked
    
    def accuracy_report(self):
        """Report accuracy by grade"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        print("=" * 55)
        print("  OUTCOME ACCURACY REPORT")
        print("=" * 55)
        
        c.execute("""SELECT grade, COUNT(*), 
                     SUM(CASE WHEN outcome_result IN ('TP_HIT','PROFIT') THEN 1 ELSE 0 END),
                     ROUND(AVG(outcome_pnl_pips), 1)
                     FROM research_decisions WHERE outcome_result IS NOT NULL
                     GROUP BY grade ORDER BY grade""")
        
        for row in c.fetchall():
            grade, total, wins, avg_pnl = row
            wr = wins/total*100 if total > 0 else 0
            print(f"  Grade {grade}: {total} tracked, {wr:.0f}% profitable, avg {avg_pnl} pips")
        
        c.execute("""SELECT pair, COUNT(*), 
                     SUM(CASE WHEN outcome_result IN ('TP_HIT','PROFIT') THEN 1 ELSE 0 END)
                     FROM research_decisions WHERE outcome_result IS NOT NULL
                     GROUP BY pair HAVING COUNT(*) >= 5
                     ORDER BY SUM(CASE WHEN outcome_result IN ('TP_HIT','PROFIT') THEN 1 ELSE 0 END)*1.0/COUNT(*) DESC""")
        
        print("\n  By Pair (min 5 tracked):")
        for row in c.fetchall():
            wr = row[2]/row[1]*100 if row[1] > 0 else 0
            print(f"  {row[0]:10s}: {row[1]:3d} tracked, {wr:.0f}% profitable")
        
        conn.close()
        print("=" * 55)


if __name__ == "__main__":
    tracker = OutcomeTracker()
    tracked = tracker.track_outcomes(minutes_forward=60)
    print(f"Tracked {tracked} outcomes")
    if tracked > 0:
        tracker.accuracy_report()
