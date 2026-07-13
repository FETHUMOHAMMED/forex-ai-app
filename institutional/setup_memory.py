"""
Volume 6: Setup Memory Database
Stores every trade with full institutional context for pattern recognition.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'trades.db')

def init_memory():
    """Create trade memory table for institutional learning"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS trade_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            pair TEXT,
            direction TEXT,
            
            -- Volume 1: Microstructure
            institutional_bias TEXT,
            microstructure_score REAL,
            dealer_pressure TEXT,
            liquidity_event TEXT,
            continuation_prob REAL,
            
            -- Volume 2: Liquidity
            nearest_liquidity TEXT,
            pool_distance_pips REAL,
            sweep_probability REAL,
            inst_interest TEXT,
            liquidity_score REAL,
            
            -- Volume 3: Structure
            market_phase TEXT,
            structure_bias TEXT,
            structure_score REAL,
            trend_quality TEXT,
            expansion_state TEXT,
            institutional_cycle TEXT,
            
            -- Trade details
            ml_confidence REAL,
            session TEXT,
            entry_price REAL,
            exit_price REAL,
            stop_loss REAL,
            take_profit REAL,
            result_r REAL,
            pnl REAL,
            win_loss TEXT,
            
            -- Decision
            decision_grade TEXT,
            opportunity_score REAL,
            expected_value_r REAL
        )
    ''')
    
    # Add indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_memory_pair ON trade_memory(pair)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_memory_session ON trade_memory(session)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_memory_phase ON trade_memory(market_phase)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_memory_bias ON trade_memory(institutional_bias)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_memory_result ON trade_memory(win_loss)')
    
    conn.commit()
    conn.close()
    print('[MEMORY] Trade memory database initialized')

def log_trade_to_memory(pair: str, direction: str, signal: dict, 
                        ms_result=None, liq_result=None, struct_result=None,
                        decision=None, pnl: float = 0, entry: float = 0, 
                        exit_p: float = 0, sl: float = 0, tp: float = 0):
    """Log a completed trade to institutional memory"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Calculate R multiple
    risk = abs(entry - sl) if entry and sl else 0
    result_r = (pnl / risk) if risk > 0 else 0
    
    # Determine session
    hour = datetime.now(timezone.utc).hour
    if 0 <= hour < 7: session = 'ASIAN'
    elif 7 <= hour < 13: session = 'LONDON'
    elif 13 <= hour < 16: session = 'OVERLAP'
    elif 16 <= hour < 22: session = 'NY'
    else: session = 'LATE'
    
    c.execute('''
        INSERT INTO trade_memory (
            timestamp, pair, direction,
            institutional_bias, microstructure_score, dealer_pressure, 
            liquidity_event, continuation_prob,
            nearest_liquidity, pool_distance_pips, sweep_probability,
            inst_interest, liquidity_score,
            market_phase, structure_bias, structure_score, trend_quality,
            expansion_state, institutional_cycle,
            ml_confidence, session, entry_price, exit_price,
            stop_loss, take_profit, result_r, pnl, win_loss,
            decision_grade, opportunity_score, expected_value_r
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now(timezone.utc).isoformat(), pair, direction,
        ms_result.institutional_bias if ms_result else None,
        ms_result.microstructure_score if ms_result else None,
        ms_result.dealer_pressure if ms_result else None,
        ms_result.liquidity_state if ms_result else None,
        ms_result.continuation_probability if ms_result else None,
        liq_result.nearest_liquidity if liq_result else None,
        0 if liq_result else None,
        liq_result.sweep_strength if liq_result else None,
        str(liq_result.sweep_direction or "NONE") if liq_result else None,
        liq_result.liquidity_score if liq_result else None,
        struct_result.market_phase if struct_result else None,
        struct_result.structure_bias if struct_result else None,
        struct_result.structure_score if struct_result else None,
        "UNKNOWN" if struct_result else None,
        "UNKNOWN" if struct_result else None,
        "UNKNOWN" if struct_result else None,
        signal.get('confidence', 0) if signal else 0,
        session, entry, exit_p, sl, tp,
        round(result_r, 2), round(pnl, 2),
        'WIN' if pnl > 0 else 'LOSS',
        decision.grade if decision else None,
        decision.opportunity_score if decision else None,
        decision.expected_value_r if decision else None
    ))
    
    conn.commit()
    conn.close()
    
    return result_r

def query_similar_setups(pair: str, direction: str, market_phase: str = None,
                         structure_bias: str = None, session: str = None) -> dict:
    """Find historically similar setups and their outcomes"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    query = 'SELECT COUNT(*), SUM(CASE WHEN win_loss="WIN" THEN 1 ELSE 0 END), AVG(result_r) FROM trade_memory WHERE pair=? AND direction=?'
    params = [pair, direction]
    
    if market_phase:
        query += ' AND market_phase=?'
        params.append(market_phase)
    if structure_bias:
        query += ' AND structure_bias=?'
        params.append(structure_bias)
    if session:
        query += ' AND session=?'
        params.append(session)
    
    c.execute(query, params)
    row = c.fetchone()
    conn.close()
    
    total = row[0] or 0
    wins = row[1] or 0
    avg_r = row[2] or 0
    
    return {
        'total': total,
        'wins': wins,
        'win_rate': (wins / total * 100) if total > 0 else 0,
        'avg_r': round(avg_r, 2)
    }

# Initialize on import
init_memory()