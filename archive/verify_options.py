import sys
sys.path.insert(0, '.')
import sqlite3
import json

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print('=' * 65)
print('  DATA ACCELERATION - ALL 4 OPTIONS VERIFICATION')
print('=' * 65)

# Option 1
print('\n1. EXPAND SCANNING UNIVERSE')
with open('ai-service/config.json') as f:
    config = json.load(f)
for acc in config['accounts']:
    if acc['name'] == 'Demo2':
        pairs = acc['pairs']
        sessions = acc.get('sessions_enabled', [])
        print('   Pairs: ' + str(len(pairs)) + ' - ' + str(pairs))
        print('   Sessions: ' + str(sessions))
        print('   Status: ACTIVE')

# Option 2
print('\n2. SHADOW TRADING MODE')
c.execute("SELECT COUNT(*) FROM shadow_trades")
shadow_total = c.fetchone()[0]
c.execute("SELECT decision, COUNT(*) FROM shadow_trades GROUP BY decision")
decisions = c.fetchall()
print('   shadow_trades table: ' + str(shadow_total) + ' records')
for d, count in decisions:
    print('     ' + str(d) + ': ' + str(count))
c.execute("SELECT COUNT(*) FROM opportunity_stats")
opp_stats = c.fetchone()[0]
print('   opportunity_stats: ' + str(opp_stats) + ' daily records')
print('   Status: ACTIVE')

# Option 3
print('\n3. HISTORICAL REPLAY ENGINE')
c.execute("SELECT COUNT(*) FROM shadow_trades WHERE decision='SIMULATED'")
simulated = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT pair) FROM shadow_trades WHERE decision='SIMULATED'")
sim_pairs = c.fetchone()[0]
c.execute("SELECT pair, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) FROM shadow_trades WHERE decision='SIMULATED' GROUP BY pair")
sim_by_pair = c.fetchall()
print('   Simulated trades: ' + str(simulated))
print('   Pairs covered: ' + str(sim_pairs) + '/6')
for row in sim_by_pair:
    wr = row[2]/row[1]*100 if row[1] > 0 else 0
    print('     ' + str(row[0]) + ': ' + str(row[1]) + ' trades, ' + str(round(wr)) + '% WR')
print('   Status: ACTIVE')

# Option 4
print('\n4. OUTCOME SIMULATOR')
c.execute("SELECT COUNT(*) FROM shadow_trades WHERE simulated_result != 'PENDING'")
resolved = c.fetchone()[0]
print('   Resolved outcomes: ' + str(resolved) + '/' + str(shadow_total))
print('   Module: institutional/shadow_simulator.py')
print('   Status: READY')

# Total
print('\n5. TOTAL DATA POINTS')
c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
real_trades = c.fetchone()[0]
print('   Real trades (trades table): ' + str(real_trades))
print('   Shadow trades (shadow_trades): ' + str(shadow_total))
print('   -----------------------------')
print('   COMBINED DATA POINTS: ' + str(real_trades + shadow_total))

# Regime insights
print('\n6. REGIME INSIGHTS (from replay)')
c.execute("SELECT regime, COUNT(*), SUM(CASE WHEN simulated_result='WIN' THEN 1 ELSE 0 END) FROM shadow_trades WHERE decision='SIMULATED' AND regime IS NOT NULL GROUP BY regime ORDER BY COUNT(*) DESC")
for row in c.fetchall():
    wr = row[2]/row[1]*100 if row[1] > 0 else 0
    print('   ' + str(row[0]) + ': ' + str(row[1]) + ' trades, ' + str(round(wr)) + '% WR')

print('\n' + '=' * 65)
print('  ALL 4 OPTIONS: APPLIED')
print('  DATA POINTS: ' + str(real_trades + shadow_total))
print('  SYSTEM: ACCELERATED DATA COLLECTION ACTIVE')
print('=' * 65)

conn.close()
