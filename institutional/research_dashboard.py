"""
Volume 7.5: Institutional Research Dashboard
Quick visibility into what makes money and what doesn't.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'trades.db')

def dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print('=' * 60)
    print('  INSTITUTIONAL RESEARCH DASHBOARD')
    print('=' * 60)
    print()
    
    # Overall stats
    c.execute('SELECT COUNT(*), SUM(pnl), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) FROM trades WHERE pnl IS NOT NULL')
    total, net, wins = c.fetchone()
    c.execute('SELECT AVG(pnl) FROM trades WHERE pnl > 0')
    avg_win = c.fetchone()[0] or 0
    c.execute('SELECT AVG(ABS(pnl)) FROM trades WHERE pnl < 0')
    avg_loss = c.fetchone()[0] or 0
    
    print('1. OVERALL PERFORMANCE')
    print(f'   Trades: {total or 0}')
    print(f'   Wins: {wins or 0} | Losses: {(total or 0) - (wins or 0)}')
    wr = (wins/total*100) if total else 0
    print(f'   Win Rate: {wr:.1f}%')
    print(f'   Net PnL: ${net or 0:.2f}')
    print(f'   Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f}')
    print()
    
    # By pair
    c.execute('''SELECT pair, COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2)
                 FROM trades WHERE pnl IS NOT NULL GROUP BY pair ORDER BY SUM(pnl) DESC''')
    pairs = c.fetchall()
    print('2. BY PAIR')
    print(f'   {"Pair":10s} {"Trades":>6s} {"WR":>6s} {"PnL":>10s}')
    print('   ' + '-' * 35)
    for p in pairs:
        wr2 = (p[2]/p[1]*100) if p[1] else 0
        print(f'   {p[0]:10s} {p[1]:6d} {wr2:5.0f}% ${p[3]:>8}')
    print()
    
    # By session (from timestamps)
    c.execute('''SELECT 
                 CASE WHEN CAST(strftime("%H", timestamp) AS INTEGER) BETWEEN 0 AND 6 THEN "ASIAN"
                      WHEN CAST(strftime("%H", timestamp) AS INTEGER) BETWEEN 7 AND 12 THEN "LONDON"
                      WHEN CAST(strftime("%H", timestamp) AS INTEGER) BETWEEN 13 AND 16 THEN "OVERLAP"
                      ELSE "NY" END as session,
                 COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl),2)
                 FROM trades WHERE pnl IS NOT NULL GROUP BY session ORDER BY SUM(pnl) DESC''')
    sessions = c.fetchall()
    print('3. BY SESSION')
    print(f'   {"Session":10s} {"Trades":>6s} {"WR":>6s} {"PnL":>10s}')
    print('   ' + '-' * 35)
    for s in sessions:
        wr3 = (s[2]/s[1]*100) if s[1] else 0
        print(f'   {s[0]:10s} {s[1]:6d} {wr3:5.0f}% ${s[3]:>8}')
    print()
    
    # Institutional data coverage
    c.execute('SELECT COUNT(*) FROM trades WHERE institutional_bias IS NOT NULL AND pnl IS NOT NULL')
    inst_count = c.fetchone()[0]
    print('4. INSTITUTIONAL DATA COVERAGE')
    print(f'   Trades with inst data: {inst_count}/{total or 0}')
    pct = (inst_count/total*100) if total else 0
    print(f'   Coverage: {pct:.0f}%')
    print(f'   Target: 50 for initial validation')
    print()
    
    # Memory tables
    c.execute('SELECT COUNT(*) FROM trade_memory')
    mem = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM performance_memory')
    perf = c.fetchone()[0]
    print('5. MEMORY DATABASES')
    print(f'   trade_memory: {mem} entries')
    print(f'   performance_memory: {perf} entries')
    print()
    
    # Open positions - sync with MT5 first
    try:
        import MetaTrader5 as mt5
        mt5.initialize()
        live_positions = mt5.positions_get()
        live_tickets = {p.ticket for p in live_positions} if live_positions else set()
        c.execute('SELECT id, ticket FROM trades WHERE exit_price IS NULL')
        for row in c.fetchall():
            if row[1] and row[1] not in live_tickets:
                c.execute("UPDATE trades SET exit_price=entry, exit_time=timestamp, pnl=0, result='UNKNOWN' WHERE id=?", (row[0],))
        conn.commit()
        mt5.shutdown()
    except Exception:
        pass
    
    c.execute('SELECT COUNT(*) FROM trades WHERE exit_price IS NULL')
    open_t = c.fetchone()[0]
    print('6. OPEN POSITIONS')
    print(f'   Currently open: {open_t}')
    if open_t:
        c.execute('SELECT pair, signal, entry, timestamp FROM trades WHERE exit_price IS NULL')
        for pos in c.fetchall():
            print(f'   {pos[0]} {pos[1]} @ {pos[2]} since {pos[3][:19]}')
    
    conn.close()
    
    print()
    print('=' * 60)
    print('  Dashboard complete. Run anytime for quick status.')
    print('=' * 60)

if __name__ == '__main__':
    dashboard()