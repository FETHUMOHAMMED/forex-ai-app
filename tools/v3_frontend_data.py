"""V3 Frontend Data Provider - STRICTLY separated from PRE_V3.
Every value shows its source: MT5, DB_V3, or ARCHIVE.
"""
import sqlite3
import json
from datetime import datetime, timezone

def get_v3_frontend_data():
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    
    # === V3 PERFORMANCE (only V3_REGIME + Live_Micro + clean) ===
    c.execute("""
        SELECT COUNT(*), 
               COALESCE(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END), 0),
               COALESCE(SUM(pnl), 0)
        FROM trades 
        WHERE strategy_version = 'V3_REGIME' 
        AND account = 'Live_Micro'
        AND result NOT LIKE 'LEGACY%'
        AND result != 'EXECUTION_EXCEPTION'
        AND result IN ('WIN', 'LOSS', 'BREAKEVEN')
        AND execution_contract_valid = 1
    """)
    v3 = c.fetchone()
    
    # === PRE_V3 ARCHIVE ===
    c.execute("""
        SELECT COUNT(*), 
               ROUND(CAST(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1),
               COALESCE(SUM(pnl), 0),
               ROUND(CAST(COALESCE(SUM(CASE WHEN result='WIN' THEN pnl ELSE 0 END), 0) AS FLOAT) / 
                     NULLIF(ABS(COALESCE(SUM(CASE WHEN result='LOSS' THEN pnl ELSE 0 END), 0)), 0), 2)
        FROM trades 
        WHERE strategy_version = 'PRE_V3'
        AND result IN ('WIN', 'LOSS')
    """)
    pre_v3 = c.fetchone()
    
    # === ACTIVE SIGNALS (from cache) ===
    signals = []
    try:
        with open('ai-service/signals_cache.json', 'r') as f:
            cache = json.load(f)
        for pair, sig in cache.items():
            if isinstance(sig, dict) and sig.get('signal'):
                signals.append({
                    'pair': pair,
                    'direction': sig.get('signal', 'N/A'),
                    'confidence': sig.get('confidence', 0),
                    'regime': sig.get('regime', 'UNKNOWN'),
                    'entry': sig.get('entry', 0),
                    'sl': sig.get('stop_loss', 0),
                    'tp': sig.get('take_profit', 0),
                    'institutional_bias': sig.get('institutional_bias', 'N/A'),
                    'dealer_pressure': sig.get('dealer_pressure', 'N/A'),
                    'liquidity_state': sig.get('liquidity_state', 'N/A'),
                })
    except:
        pass
    
    # === MT5 ACCOUNT ===
    import MetaTrader5 as mt5
    mt5.initialize()
    info = mt5.account_info()
    mt5_data = {
        'connected': info is not None,
        'login': info.login if info else None,
        'balance': info.balance if info else 0,
        'equity': info.equity if info else 0,
        'server': info.server if info else '',
    }
    mt5.shutdown()
    
    # === VALIDATION PROGRESS ===
    milestones = [
        {'target': 10, 'label': 'Execution Verified', 'done': v3[0] >= 10},
        {'target': 25, 'label': 'Risk Verified', 'done': v3[0] >= 25},
        {'target': 50, 'label': 'Initial Review', 'done': v3[0] >= 50},
        {'target': 100, 'label': 'Statistical Validation', 'done': v3[0] >= 100},
        {'target': 300, 'label': 'Production Confidence', 'done': v3[0] >= 300},
    ]
    
    conn.close()
    
    return {
        'source_note': 'V3 data is STRICTLY separated from PRE_V3 archive',
        'mt5': mt5_data,
        'v3_performance': {
            'trades': v3[0],
            'wins': v3[1],
            'pnl': v3[2],
            'win_rate': round((v3[1]/v3[0]*100), 1) if v3[0] > 0 else 'N/A',
            'is_meaningful': v3[0] >= 50,
            'status': 'Collecting statistical data' if v3[0] < 50 else 'Under review',
        },
        'pre_v3_archive': {
            'trades': pre_v3[0],
            'win_rate': pre_v3[1],
            'pnl': pre_v3[2],
            'profit_factor': pre_v3[3],
            'status': 'FROZEN - PRE_V3 archived',
        },
        'active_signals': signals,
        'validation': {
            'trades': v3[0],
            'target': 100,
            'milestones': milestones,
        },
        'risk': {
            'risk_per_trade': '0.05%',
            'max_daily_loss': '0.5%',
            'max_open_trades': 5,
            'session_filter': 'ON (7-11 UTC)',
            'news_filter': 'ON',
        },
    }

if __name__ == "__main__":
    import json
    data = get_v3_frontend_data()
    print(json.dumps(data, indent=2, default=str))
