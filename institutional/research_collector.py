"""
Volume 9.6: Research Collector
Fast decision collection without execution risk.
Records ALL AI decisions across expanded pairs for learning.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List

class ResearchCollector:
    """
    Collects AI decisions at high speed without execution.
    Expanded pairs, lower thresholds, shadow-only mode.
    """
    
    def __init__(self):
        self.db_path = "ai-service/trades.db"
        
        # Research pairs - expanded for data collection
        self.research_pairs = [
            "USDJPY", "NZDUSD", "EURUSD", "GBPUSD", "USDCAD",
            "AUDUSD", "USDCHF", "USDSGD", "EURJPY", "GBPJPY"
        ]
        
        # Research thresholds (lower than production)
        self.min_confidence = 0.48
        self.ict_threshold = 2  # Even lower for research
        
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS research_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            pair TEXT NOT NULL,
            signal TEXT,
            confidence REAL,
            ict_buy INTEGER,
            ict_sell INTEGER,
            regime TEXT,
            institutional_score REAL,
            dealer_pressure TEXT,
            liquidity_state TEXT,
            structure_bias TEXT,
            trend_aligned INTEGER,
            decision TEXT,
            grade TEXT,
            quality_score REAL,
            source TEXT DEFAULT 'research',
            created_at TEXT DEFAULT (datetime('now'))
        )''')
        conn.commit()
        conn.close()
    
    def collect_cycle(self) -> int:
        """Run one collection cycle across all research pairs"""
        mt5.initialize()
        decisions = 0
        
        for pair in self.research_pairs:
            try:
                decision = self._analyze_pair(pair)
                if decision:
                    self._save_decision(decision)
                    decisions += 1
            except:
                pass
        
        mt5.shutdown()
        return decisions
    
    def _analyze_pair(self, pair: str) -> Dict:
        """Analyze a single pair with research thresholds"""
        symbol = pair + 'm'
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
        
        if rates is None or len(rates) < 50:
            return None
        
        df = pd.DataFrame(rates)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        
        # Get current price
        current = float(df['close'].iloc[-1])
        
        # Simple ML simulation
        ml_buy = float(df['close'].iloc[-1]) > float(df['close'].iloc[-20])
        ml_conf = 0.48 + (abs(current - float(df['close'].iloc[-20])) / current * 100)
        ml_conf = min(0.75, ml_conf)
        
        signal = "BUY" if ml_buy else "SELL"
        
        # Simple ICT simulation
        recent_high = float(df['high'].iloc[-10:].max())
        recent_low = float(df['low'].iloc[-10:].min())
        ict_buy = current > recent_high * 0.999
        ict_sell = current < recent_low * 1.001
        
        # Institutional analysis
        from institutional.market_microstructure import MarketMicrostructure
        from institutional.liquidity_intelligence import LiquidityIntelligence
        from institutional.institutional_structure import InstitutionalStructure
        
        df_copy = df.copy()
        df_copy['time'] = pd.to_datetime(df_copy['time'], unit='s')
        df_copy.set_index('time', inplace=True)
        
        mm = MarketMicrostructure()
        liq = LiquidityIntelligence()
        struct = InstitutionalStructure()
        
        ms = mm.analyze(pair, df_copy)
        lq = liq.analyze(pair, df_copy)
        st = struct.analyze(pair, df_copy)
        
        # Regime
        regime = st.structure_bias if st else "UNKNOWN"
        
        # Trend check
        h1_trend = "BULLISH" if current > float(df['close'].iloc[-50]) else "BEARISH"
        trend_aligned = (signal == "BUY" and h1_trend == "BULLISH") or (signal == "SELL" and h1_trend == "BEARISH")
        
        # Quality score
        from institutional.trade_scorer import scorer
        signal_dict = {
            'signal': signal,
            'confidence': ml_conf,
            'strength': 'MEDIUM',
            'institutional_bias': ms.institutional_bias,
            'institutional_score': ms.microstructure_score,
            'continuation_prob': ms.continuation_probability,
            'regime': regime
        }
        quality = scorer.score_trade(pair, signal_dict)
        
        return {
            'pair': pair,
            'signal': signal,
            'confidence': round(ml_conf, 3),
            'ict_buy': ict_buy,
            'ict_sell': ict_sell,
            'regime': regime,
            'institutional_score': round(ms.microstructure_score, 1),
            'dealer_pressure': ms.dealer_pressure,
            'liquidity_state': lq.liquidity_state,
            'structure_bias': st.structure_bias,
            'trend_aligned': trend_aligned,
            'decision': quality.recommendation,
            'grade': quality.grade,
            'quality_score': round(quality.total_score, 1)
        }
    
    def _save_decision(self, decision: Dict):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        c.execute('''INSERT INTO research_decisions 
            (timestamp, pair, signal, confidence, ict_buy, ict_sell, regime,
             institutional_score, dealer_pressure, liquidity_state, structure_bias,
             trend_aligned, decision, grade, quality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (now, decision['pair'], decision['signal'], decision['confidence'],
             decision['ict_buy'], decision['ict_sell'], decision['regime'],
             decision['institutional_score'], decision['dealer_pressure'],
             decision['liquidity_state'], decision['structure_bias'],
             decision['trend_aligned'], decision['decision'], decision['grade'],
             decision['quality_score']))
        conn.commit()
        conn.close()
    
    def run_continuous(self, cycles: int = 100, interval: int = 5):
        """Run multiple collection cycles"""
        total = 0
        for i in range(cycles):
            count = self.collect_cycle()
            total += count
            if count > 0:
                print(f"  Cycle {i+1}: {count} decisions (total: {total})")
            import time
            time.sleep(interval)
        return total
    
    def stats(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM research_decisions")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT pair) FROM research_decisions")
        pairs = c.fetchone()[0]
        c.execute("SELECT decision, COUNT(*) FROM research_decisions GROUP BY decision")
        by_decision = c.fetchall()
        conn.close()
        
        print(f"Research Decisions: {total} across {pairs} pairs")
        for d, count in by_decision:
            print(f"  {d}: {count}")


if __name__ == "__main__":
    rc = ResearchCollector()
    print("Research Collector - collecting 50 cycles...")
    total = rc.run_continuous(cycles=50, interval=2)
    print(f"\nTotal collected: {total}")
    rc.stats()
