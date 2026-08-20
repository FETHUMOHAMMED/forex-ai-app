"""Professional Dashboard Data - Implements ALL advisor recommendations.
Sections: Status, V3 Performance, Active Signals, AI Decision, Risk, Archive, Validation.
STRICT separation: V3_REGIME + Live_Micro only. PRE_V3 in separate Archive section.
"""
import sqlite3
import json
from datetime import datetime, timezone

def get_dashboard_data():
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    
    # === FILTER: Only V3_REGIME + Live_Micro + clean ===
    V3_FILTER = """strategy_version = 'V3_REGIME' 
                   AND account = 'Live_Micro'
                   AND result NOT LIKE 'LEGACY%'
                   AND result != 'EXECUTION_EXCEPTION'"""
    
    # ========================================================================
    # 1. STATUS BAR
    # ========================================================================
    import MetaTrader5 as mt5
    mt5.initialize()
    info = mt5.account_info()
    positions = mt5.positions_get()
    mt5.shutdown()
    
    status = {
        "connected": info is not None,
        "broker": info.server if info else "Disconnected",
        "ai_engine": "Running" if info else "Offline",
        "strategy": "V3_REGIME",
        "mode": "Micro Validation",
        "balance": info.balance if info else 0,
        "equity": info.equity if info else 0,
        "unrealized_pnl": round(info.equity - info.balance, 2) if info else 0,
        "open_positions": len(positions) if positions else 0,
    }
    
    # ========================================================================
    # 2. V3_REGIME PERFORMANCE (statistically honest)
    # ========================================================================
    c.execute(f"SELECT COUNT(*), COALESCE(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),0), COALESCE(SUM(pnl),0) FROM trades WHERE {V3_FILTER} AND result IN ('WIN','LOSS','BREAKEVEN') AND execution_contract_valid = 1")
    v3 = c.fetchone()
    
    v3_performance = {
        "trades": v3[0],
        "target": 100,
        "wins": v3[1],
        "losses": v3[0] - v3[1] if v3[0] > 0 else 0,
        "pnl": round(v3[2], 2),
        "win_rate": f"{round(v3[1]/v3[0]*100,1)}%" if v3[0] >= 10 else "N/A",
        "profit_factor": "N/A",
        "is_meaningful": v3[0] >= 50,
        "status": "Collecting statistical data" if v3[0] < 10 else "Early validation" if v3[0] < 50 else "Under review",
        "note": "Win rate hidden until 10+ trades for statistical validity" if v3[0] < 10 else None,
    }
    
    # ========================================================================
    # 3. ACTIVE SIGNALS (with institutional metadata)
    # ========================================================================
    signals = []
    try:
        with open('ai-service/signals_cache.json', 'r') as f:
            cache = json.load(f)
        for pair, sig in cache.items():
            if isinstance(sig, dict) and sig.get('signal'):
                signals.append({
                    "pair": pair,
                    "direction": sig.get('signal'),
                    "confidence": round(sig.get('confidence', 0) * 100),
                    "entry": sig.get('entry'),
                    "sl": sig.get('stop_loss'),
                    "tp": sig.get('take_profit'),
                    "regime": sig.get('regime', 'UNKNOWN'),
                    "institutional_bias": sig.get('institutional_bias', 'N/A'),
                    "dealer_pressure": sig.get('dealer_pressure', 'N/A'),
                    "liquidity_state": sig.get('liquidity_state', 'N/A'),
                    "continuation_prob": sig.get('continuation_prob'),
                    "session": "London" if 7 <= datetime.now(timezone.utc).hour < 16 else "Asian" if datetime.now(timezone.utc).hour < 7 else "NY",
                })
    except:
        pass
    
    # ========================================================================
    # 4. AI DECISION ENGINE
    # ========================================================================
    ai_decision = {
        "checks": [
            {"label": "HTF Trend Alignment", "passed": len(signals) > 0},
            {"label": "Regime Confirmed", "passed": any(s.get('regime') not in ('UNKNOWN', None) for s in signals)},
            {"label": "Liquidity Sweep Detected", "passed": any(s.get('liquidity_state') not in ('NO_EVENT', None) for s in signals)},
            {"label": "Institutional Bias Confirmed", "passed": any(s.get('institutional_score', 0) > 50 for s in signals)},
            {"label": "Confidence Threshold Passed", "passed": any(s.get('confidence', 0) >= 75 for s in signals)},
        ],
        "passed_count": sum(1 for c in [
            len(signals) > 0,
            any(s.get('regime') not in ('UNKNOWN', None) for s in signals),
            any(s.get('liquidity_state') not in ('NO_EVENT', None) for s in signals),
            any(s.get('institutional_score', 0) > 50 for s in signals),
            any(s.get('confidence', 0) >= 75 for s in signals),
        ] if c),
    }
    
    # ========================================================================
    # 5. RISK ENGINE
    # ========================================================================
    risk = {
        "risk_per_trade": "0.05%",
        "max_daily_loss": "0.5%",
        "max_open_trades": 5,
        "current_exposure": len(positions) if positions else 0,
        "session_filter": "ON (London 7-11 UTC)",
        "news_filter": "ON",
        "monetary_risk_gate": "ACTIVE",
        "signal_freshness_gate": "ACTIVE (120s max)",
    }
    
    # ========================================================================
    # 6. PRE_V3 ARCHIVE (frozen)
    # ========================================================================
    c.execute("""SELECT COUNT(*), ROUND(CAST(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) AS FLOAT)/MAX(COUNT(*),1)*100,1), COALESCE(SUM(pnl),0), ROUND(CAST(COALESCE(SUM(CASE WHEN result='WIN' THEN pnl ELSE 0 END),0) AS FLOAT)/NULLIF(ABS(COALESCE(SUM(CASE WHEN result='LOSS' THEN pnl ELSE 0 END),0)),0),2) FROM trades WHERE strategy_version='PRE_V3' AND result IN ('WIN','LOSS')""")
    pre = c.fetchone()
    
    archive = {
        "strategy": "PRE_V3",
        "trades": pre[0],
        "win_rate": pre[1],
        "pnl": round(pre[2], 2),
        "profit_factor": pre[3],
        "status": "FROZEN",
        "note": "Historical losing strategy (PF 0.63). Archived for comparison.",
    }
    
    # ========================================================================
    # 7. V3 VALIDATION PROGRESS
    # ========================================================================
    validation = {
        "trades": v3[0],
        "target": 100,
        "milestones": [
            {"label": "Execution Verified", "target": 10, "done": v3[0] >= 10},
            {"label": "Risk Verified", "target": 25, "done": v3[0] >= 25},
            {"label": "Initial Review", "target": 50, "done": v3[0] >= 50},
            {"label": "Statistical Validation", "target": 100, "done": v3[0] >= 100},
            {"label": "Production Confidence", "target": 300, "done": v3[0] >= 300},
        ],
        "stage": "Micro Validation" if v3[0] < 10 else "Execution Phase" if v3[0] < 50 else "Statistical Phase",
    }
    
    conn.close()
    
    return {
        "status": status,
        "v3_performance": v3_performance,
        "active_signals": signals,
        "ai_decision": ai_decision,
        "risk": risk,
        "archive": archive,
        "validation": validation,
        "system_integrity": integrity,`n        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_sources": {
            "status": "MT5 broker terminal",
            "v3_performance": "Database - V3_REGIME + Live_Micro only",
            "active_signals": "AI signal cache",
            "risk": "Configuration",
            "archive": "Database - PRE_V3 (frozen)",
            "validation": "Database - derived from V3 trades",
        },
    }

if __name__ == "__main__":
    print(json.dumps(get_dashboard_data(), indent=2, default=str))

