"""Unified Dashboard Service - Single source of truth for all dashboard data."""
import sqlite3, json, os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'ai-service', 'trades.db')

def get_dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2), ROUND(AVG(CASE WHEN pnl>0 THEN pnl END),2), ROUND(AVG(CASE WHEN pnl<0 THEN pnl END),2), ROUND(AVG(confidence),3) FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL")
    r = c.fetchone()
    t,w,l,pnl,aw,al,ac = r
    wr = round(w/t*100,1) if t>0 else 0
    
    c.execute("SELECT COUNT(*), ROUND(SUM(pnl),2) FROM trades WHERE strategy_version='PRE_V3' AND pnl IS NOT NULL")
    pre_t, pre_pnl = c.fetchone()
    
    c.execute("SELECT institutional_bias, COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2) FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL GROUP BY institutional_bias")
    regimes = [{"regime":row[0],"trades":row[1],"wins":row[2],"pnl":row[3]} for row in c.fetchall()]
    
    buckets = [(0.75,0.80),(0.80,0.85),(0.85,0.90),(0.90,1.01)]
    confidence = []
    for lo,hi in buckets:
        c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2) FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL AND confidence>=? AND confidence<?",(lo,hi))
        r2 = c.fetchone()
        confidence.append({"range":str(int(lo*100))+"-"+str(int(hi*100))+"%","trades":r2[0],"wins":r2[1] or 0,"pnl":r2[2] or 0})
    
    if t < 10: stat_conf = "LOW"
    elif t < 50: stat_conf = "EARLY"
    elif t < 100: stat_conf = "MEDIUM"
    elif t < 300: stat_conf = "HIGH"
    else: stat_conf = "INSTITUTIONAL"
    
        # MT5 positions
    try:
        import os
        import MetaTrader5 as mt5
        mt5.initialize()
        live_account = int(os.getenv("EXNESS_LIVE_ACCOUNT"))
        live_password = os.getenv("EXNESS_LIVE_PASSWORD")
        live_server = os.getenv("EXNESS_LIVE_SERVER", "Exness-MT5Real10")
        if not live_account or not live_password:
            raise RuntimeError("EXNESS_LIVE_ACCOUNT and EXNESS_LIVE_PASSWORD must be set")
        if not mt5.login(live_account, password=live_password, server=live_server):
            raise RuntimeError(f"MT5 login failed: {mt5.last_error()}")
        pos = mt5.positions_get()
        open_positions = len(pos) if pos else 0
        mt5.shutdown()
    except Exception:
        open_positions = 0
    
    conn.close()
    
    return {
        "header": {"title":"FOREX-AI-APP","subtitle":"Institutional AI Trading Platform","version":"V3_REGIME","environment":"LIVE MICRO","broker":"Exness","server":"Connected","research_stage":"Micro Validation"},
        "research": {"trades":t,"target":100,"progress":round(t/100*100,1) if t>0 else 0,"milestones":[{"trades":10,"label":"Execution Verified","done":t>=10},{"trades":25,"label":"Risk Verified","done":t>=25},{"trades":50,"label":"Initial Review","done":t>=50},{"trades":100,"label":"Statistical Validation","done":t>=100},{"trades":300,"label":"Production Ready","done":t>=300}]},
        "performance": {"trades":t,"wins":w,"losses":l,"win_rate":wr,"net_pnl":pnl or 0,"avg_win":aw,"avg_loss":al,"avg_confidence":ac},
        "regimes": regimes,
        "confidence_buckets": confidence,
        "statistical_confidence": stat_conf, "open_positions": open_positions,
        "archive": {"version":"PRE_V3","trades":pre_t,"win_rate":26.7,"profit_factor":0.63,"pnl":pre_pnl,"status":"ARCHIVED","reason":"Weak Institutional Filtering"}
    }

if __name__ == "__main__":
    print(json.dumps(get_dashboard(), indent=2))
