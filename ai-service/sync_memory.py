import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('trades.db')
c = conn.cursor()

c.execute('''SELECT id, pair, timestamp, signal, entry, exit_price, exit_time, pnl, pnl_percent, result,
             institutional_bias, institutional_score, dealer_pressure, liquidity_state, continuation_prob
             FROM trades WHERE pnl IS NOT NULL''')
trades = c.fetchall()

c.execute('DELETE FROM trade_memory')
c.execute('DELETE FROM performance_memory')

inserted = 0
for t in trades:
    tid, pair, ts, signal, entry, exit_p, exit_ts, pnl, pnl_pct, result, inst_bias, inst_score, dp, liq_state, cont_prob = t
    
    try:
        dt = datetime.fromisoformat(ts)
        hour = dt.hour
        if 3 <= hour < 12:
            session = 'LONDON'
        elif 12 <= hour < 20:
            session = 'NY'
        elif 20 <= hour or hour < 3:
            session = 'ASIAN'
        else:
            session = 'OVERLAP'
    except:
        session = 'UNKNOWN'
    
    now = datetime.now(timezone.utc).isoformat()
    
    # trade_memory
    c.execute('''INSERT INTO trade_memory 
        (timestamp, pair, direction, institutional_bias, microstructure_score, dealer_pressure,
         liquidity_event, continuation_prob, liquidity_score, market_phase, structure_bias,
         structure_score, ml_confidence, session, entry_price, exit_price, pnl, win_loss,
         decision_grade, opportunity_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        now, pair, signal, inst_bias, inst_score, dp,
        liq_state, cont_prob, inst_score, 'STABLE', inst_bias,
        inst_score or 0, 0.5, session, entry, exit_p, pnl, result,
        'B' if result == 'WIN' else 'D', inst_score or 0
    ))
    
    # performance_memory - matching actual schema
    c.execute('''INSERT INTO performance_memory
        (timestamp, pair, session, direction, entry_time, exit_time, pnl, result_r, win_loss,
         institutional_score, liquidity_state, structure_phase, dealer_pressure, setup_type,
         decision_quality, success_reason, failure_reason, edge_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        now, pair, session, signal, ts, exit_ts or ts, pnl, pnl_pct or 0, result,
        inst_score or 0, liq_state or 'UNKNOWN', inst_bias or 'NEUTRAL', dp or 'NEUTRAL', 'INSTITUTIONAL',
        'B' if result == 'WIN' else 'D', '', '', inst_score or 0, now
    ))
    
    inserted += 1

conn.commit()

c.execute('SELECT COUNT(*) FROM trade_memory')
tm = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM performance_memory')
pm = c.fetchone()[0]
print('Memory synced: ' + str(inserted) + ' trades')
print('trade_memory: ' + str(tm))
print('performance_memory: ' + str(pm))

conn.close()
