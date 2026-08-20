"""
Daemon V2 - Refactored AI service using unified Core Pipeline.
Replaces ai_service_daemon.py and real_ai_service.py.
One signal path, one TradeSignal model, clean separation.
"""
import sys, os, json, time, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, wait

from core.signal_pipeline_v2 import SignalPipelineV2 as SignalPipeline
from core.regime_strategy import strategy as regime_strategy
from ml.inference import predictor as ml_predictor
from shared.trade_signal import TradeSignal

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger('daemon_v2')

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
CACHE_PATH = os.path.join(BASE_DIR, 'signals_cache.json')

class DaemonV2:
    """Refactored AI daemon - clean, single pipeline"""
    
    def __init__(self):
        with open(CONFIG_PATH) as f:
            self.config = json.load(f)
        
        # Read pairs from Demo2 account config
        demo2_pairs = ['EURUSD']
        for acc in self.config.get('accounts', []):
            if acc.get('name') == 'Demo2':
                demo2_pairs = acc.get('pairs', ['EURUSD'])
        self.pairs = demo2_pairs
        self.blocked = {'USDCHF', 'USDSGD', 'NZDUSD', 'AUDUSD', 'EURJPY', 'GBPJPY', 'EURGBP', 'AUDJPY'}
        self.pipeline = SignalPipeline()  # V2 with independent detectors
        self.cache: List[Dict] = []
        self.version = 0
    
    def run_cycle(self):
        """One analysis cycle - generates signals for all pairs"""
        mt5.initialize()
        signals = []
        
        for pair in self.pairs:
            if pair in self.blocked:
                continue
            
            try:
                signal = self._analyze_pair(pair)
                if signal and signal.is_valid:
                    # Apply regime strategy filter
                    if regime_strategy.validate(signal):
                        signals.append(signal.to_dict())
                        logger.info(f"[SIGNAL] {pair} {signal.direction} conf={signal.confidence:.3f} inst={signal.institutional_score:.0f}")
                    else:
                        logger.debug(f"[REGIME REJECT] {pair}: {signal.rejection_reason}")
                    logger.info(f"[SIGNAL] {pair} {signal.direction} conf={signal.confidence:.3f} inst={signal.institutional_score:.0f}")
            except Exception as e:
                logger.error(f"Error {pair}: {e}")
        
        mt5.shutdown()
        
        # Update cache
        if signals:
            self.cache = signals
            self.version += 1
            self._save_cache()
        
        return len(signals)
    
    def _analyze_pair(self, pair: str) -> Optional[TradeSignal]:
        """Analyze one pair through the unified pipeline"""
        symbol = pair + 'm'
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
        
        if rates is None or len(rates) < 50:
            return None
        
        df = pd.DataFrame(rates)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # ML prediction from trained XGBoost models
        ml_signal, ml_conf = ml_predictor.predict(pair, df)
        if ml_signal is None:
            ml_signal = 'SELL' if df['close'].iloc[-1] < df['close'].iloc[-20] else 'BUY'
            ml_conf = 0.50
        
        # ICT check (simplified)
        ict_buy = df['close'].iloc[-1] > df['high'].iloc[-10:].max() * 0.998
        ict_sell = df['close'].iloc[-1] < df['low'].iloc[-10:].min() * 1.002
        
        # Generate through unified pipeline
        signal = self.pipeline.generate(pair, df, ml_signal, ml_conf, ict_buy, ict_sell)
        
        if not signal.is_valid:
            logger.debug(f"[REJECT] {pair}: {signal.rejection_reason}")
        
        return signal
    
    def _save_cache(self):
        with open(CACHE_PATH, 'w') as f:
            json.dump({'signals': self.cache, 'version': self.version, 'updated': datetime.now(timezone.utc).isoformat()}, f)
    
    def serve_forever(self, interval: int = 30):
        """Run continuously, refreshing cache every N seconds"""
        logger.info(f"Daemon V2 started - {len(self.pairs)} pairs, interval={interval}s")
        while True:
            count = self.run_cycle()
            logger.info(f"Cycle complete: {count} signals (v{self.version})")
            time.sleep(interval)


# FastAPI app for HTTP endpoint
try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()
    daemon = None
    
    @app.on_event("startup")
    async def startup():
        global daemon
        daemon = DaemonV2()
        import threading
        threading.Thread(target=daemon.serve_forever, daemon=True).start()
    
    @app.get("/signals")
    async def get_signals():
        if daemon is None:
            return JSONResponse({'signals': [], 'version': 0})
        return JSONResponse({'signals': daemon.cache, 'version': daemon.version, 'count': len(daemon.cache)})
    
    @app.get("/v3/dashboard")
    async def v3_dashboard():
    import sqlite3
    conn = sqlite3.connect("ai-service/trades.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2), ROUND(AVG(CASE WHEN pnl>0 THEN pnl END),2), ROUND(AVG(CASE WHEN pnl<0 THEN pnl END),2), ROUND(AVG(confidence),3) FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL")
    r = c.fetchone()
    t,w,l,pnl,aw,al,ac = r
    c.execute("SELECT institutional_bias, COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2) FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL GROUP BY institutional_bias")
    regimes = [{"regime":row[0],"trades":row[1],"wins":row[2],"pnl":row[3]} for row in c.fetchall()]
    buckets = [(0.75,0.80),(0.80,0.85),(0.85,0.90),(0.90,1.01)]
    confidence = []
    for lo,hi in buckets:
        c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL AND confidence>=? AND confidence<?",(lo,hi))
        r2 = c.fetchone()
        confidence.append({"range":str(int(lo*100))+"-"+str(int(hi*100))+"%","trades":r2[0],"wins":r2[1]})
    c.execute("SELECT COUNT(*), ROUND(SUM(pnl),2) FROM trades WHERE strategy_version='PRE_V3' AND pnl IS NOT NULL")
    pre = c.fetchone()
    conn.close()
    wr = round(w/t*100,1) if t>0 else 0
    pf = round((w*(aw or 0))/(l*abs(al or 0.01)),2) if l>0 and aw and al else None
    return {"strategy":"V3_REGIME","status":"collecting","performance":{"trades":t,"wins":w,"losses":l,"win_rate":wr,"profit_factor":pf,"pnl":pnl,"avg_confidence":ac},"regimes":regimes,"confidence":confidence,"research":{"target":100,"progress":t,"milestones":[10,25,50,100,300,1000]},"archive":{"version":"PRE_V3","trades":pre[0],"pnl":pre[1],"status":"frozen"}}

@app.get("/health")
    async def health():
        return {'status': 'running', 'version': daemon.version if daemon else 0}
except ImportError:
    logger.info("FastAPI not available - running in console mode")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001, log_level='info')
