"""V3 Dashboard API - Clean REST endpoint for React frontend.
STRICT separation: V3_REGIME + Live_Micro only. PRE_V3 in archive section.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

app = FastAPI(title="FOREX-AI-APP V3 Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

DB_PATH = Path(__file__).parent / "trades.db"
SIGNALS_PATH = Path(__file__).parent / "signals_cache.json"

V3_FILTER = """strategy_version = 'V3_REGIME' 
               AND account = 'Live_Micro'
               AND result NOT LIKE 'LEGACY%'
               AND result != 'EXECUTION_EXCEPTION'"""

@app.get("/v3/dashboard")
def v3_dashboard():
    """Complete V3 dashboard data - one API call"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # === V3 PERFORMANCE ===
    c.execute(f"""SELECT COUNT(*), COALESCE(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),0), 
                  COALESCE(SUM(pnl),0) FROM trades WHERE {V3_FILTER} 
                  AND result IN ('WIN','LOSS','BREAKEVEN') AND execution_contract_valid = 1""")
    v3 = c.fetchone()
    
    # === REGIME BREAKDOWN ===
    c.execute(f"""SELECT regime, COUNT(*), COALESCE(SUM(pnl),0),
                  ROUND(CAST(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) AS FLOAT)/MAX(COUNT(*),1)*100,1)
                  FROM trades WHERE {V3_FILTER} AND result IN ('WIN','LOSS','BREAKEVEN')
                  AND regime IS NOT NULL AND regime != 'UNKNOWN'
                  GROUP BY regime ORDER BY COUNT(*) DESC""")
    regimes = [{"name": r[0], "trades": r[1], "pnl": round(r[2],2), "win_rate": r[3]} for r in c.fetchall()]
    
    # === CONFIDENCE CALIBRATION ===
    confidence_ranges = [(75,80), (80,85), (85,90), (90,95), (95,100)]
    calibration = []
    for low, high in confidence_ranges:
        c.execute(f"""SELECT COUNT(*), COALESCE(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),0)
                      FROM trades WHERE {V3_FILTER} AND result IN ('WIN','LOSS','BREAKEVEN')
                      AND confidence >= ? AND confidence < ?""", (low/100, high/100))
        r = c.fetchone()
        calibration.append({"range": f"{low}-{high}%", "trades": r[0], "wins": r[1]})
    
    # === PRE_V3 ARCHIVE ===
    c.execute("""SELECT COUNT(*), ROUND(CAST(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) AS FLOAT)/MAX(COUNT(*),1)*100,1),
                  COALESCE(SUM(pnl),0), ROUND(CAST(COALESCE(SUM(CASE WHEN result='WIN' THEN pnl ELSE 0 END),0) AS FLOAT)/
                  NULLIF(ABS(COALESCE(SUM(CASE WHEN result='LOSS' THEN pnl ELSE 0 END),0)),0),2)
                  FROM trades WHERE strategy_version='PRE_V3' AND result IN ('WIN','LOSS')""")
    pre = c.fetchone()
    
    # === CURRENT SIGNALS ===
    signals = []
    try:
        with open(SIGNALS_PATH, 'r') as f:
            cache = json.load(f)
        for pair, sig in cache.items():
            if isinstance(sig, dict) and sig.get('signal'):
                signals.append({
                    "pair": pair, "direction": sig.get('signal'),
                    "confidence": round(sig.get('confidence',0)*100),
                    "regime": sig.get('regime','UNKNOWN'),
                    "dealer_pressure": sig.get('dealer_pressure','N/A'),
                    "liquidity_state": sig.get('liquidity_state','N/A'),
                    "entry": sig.get('entry'), "sl": sig.get('stop_loss'), "tp": sig.get('take_profit'),
                })
    except: pass
    
    # === VALIDATION MILESTONES ===
    milestones = [
        {"label": "Execution Verified", "target": 10, "done": v3[0] >= 10},
        {"label": "Risk Verified", "target": 25, "done": v3[0] >= 25},
        {"label": "Initial Review", "target": 50, "done": v3[0] >= 50},
        {"label": "Statistical Validation", "target": 100, "done": v3[0] >= 100},
        {"label": "Production Confidence", "target": 300, "done": v3[0] >= 300},
    ]
    
    conn.close()
    
    return {
        "strategy": "V3_REGIME",
        "performance": {
            "trades": v3[0], "wins": v3[1], "pnl": round(v3[2],2),
            "win_rate": round(v3[1]/v3[0]*100,1) if v3[0] >= 10 else None,
            "profit_factor": None, "expectancy": None,
            "is_meaningful": v3[0] >= 50,
            "status": "Collecting data" if v3[0] < 10 else "Early validation" if v3[0] < 50 else "Under review",
        },
        "regimes": regimes,
        "confidence_calibration": calibration,
        "signals": signals,
        "research": {"target": 100, "progress": v3[0], "milestones": milestones},
        "archive": {
            "strategy": "PRE_V3", "trades": pre[0], "win_rate": pre[1],
            "pnl": round(pre[2],2), "profit_factor": pre[3], "status": "FROZEN",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
def root():
    return {"service": "FOREX-AI-APP V3 Dashboard API", "version": "2.0"}

@app.get("/v3/health")
def v3_health():
    return {"status": "ok", "api": "V3 Dashboard", "version": "2.0"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    from packages.observability.metrics import get_metrics
    return get_metrics()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)


