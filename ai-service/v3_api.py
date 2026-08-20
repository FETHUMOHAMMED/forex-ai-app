"""Standalone V3 Dashboard API - runs on port 8002"""
import sqlite3, json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/v3/dashboard")
async def v3_dashboard():
    conn = sqlite3.connect("trades.db")
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
    
    return {
        "strategy":"V3_REGIME","status":"collecting",
        "performance":{"trades":t,"wins":w,"losses":l,"win_rate":wr,"profit_factor":pf,"pnl":pnl,"avg_confidence":ac},
        "regimes":regimes,"confidence":confidence,
        "research":{"target":100,"progress":t,"milestones":[10,25,50,100,300,1000]},
        "archive":{"version":"PRE_V3","trades":pre[0],"pnl":pre[1],"status":"frozen"}
    }

@app.get("/health")
async def health():
    return {"status":"running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
