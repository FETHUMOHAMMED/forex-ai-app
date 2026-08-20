"""Complete System Health Check"""
import sys, os, urllib.request, json, sqlite3, MetaTrader5 as mt5
sys.path.insert(0, '.')

print("=" * 55)
print("  FOREX-AI-APP — SYSTEM HEALTH CHECK")
print("=" * 55)

all_ok = True

# 1. MT5 Connection
print("\n1. MT5 CONNECTION")
try:
    mt5.initialize()
    info = mt5.terminal_info()
    if info and info.connected:
        print("  [OK] MT5 connected - trade_allowed=" + str(info.trade_allowed))
    else:
        print("  [FAIL] MT5 not connected")
        all_ok = False
except Exception as e:
    print("  [FAIL] " + str(e)[:60])
    all_ok = False

# 2. Daemon V2
print("\n2. DAEMON V2")
try:
    resp = urllib.request.urlopen('http://localhost:8001/health', timeout=5)
    data = json.loads(resp.read())
    print("  [OK] Daemon running - v" + str(data.get('version', 0)))
except:
    print("  [FAIL] Daemon offline")
    all_ok = False

# 3. ML Models
print("\n3. ML MODELS")
import os as _os
models = [f for f in _os.listdir('ml/models') if f.endswith('.pkl')] if _os.path.exists('ml/models') else []
print("  [OK] " + str(len(models)) + " models loaded" if len(models) == 6 else "  [WARN] " + str(len(models)) + " models")

# 4. Active Accounts
print("\n4. ACTIVE ACCOUNTS")
with open('ai-service/config.json') as f:
    config = json.load(f)
for a in config['accounts']:
    if a.get('enabled'):
        try:
            mt5.login(a['account'], password='', server=a['server'])
            acc_info = mt5.account_info()
            bal = acc_info.balance if acc_info else 'N/A'
            pos = mt5.positions_get()
            pos_count = len(pos) if pos else 0
            print("  [OK] " + a['name'] + " - balance=" + str(bal) + " positions=" + str(pos_count))
        except:
            print("  [WARN] " + a['name'] + " - cannot connect")

# 5. Database
print("\n5. DATABASE")
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
closed = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM shadow_trades")
shadow = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM strategy_memory")
mem = c.fetchone()[0]
print("  [OK] " + str(closed) + " real trades | " + str(shadow) + " shadow | " + str(mem) + " memory patterns")

# 6. V3 Strategy
print("\n6. V3 STRATEGY")
c.execute("SELECT COUNT(*), ROUND(SUM(pnl),2) FROM trades WHERE strategy_version='V3_REGIME'")
v3_t, v3_pnl = c.fetchone()
print("  [OK] " + str(v3_t) + " V3_REGIME trades, PnL $" + str(v3_pnl or 0))

# 7. Account Tagging
print("\n7. ACCOUNT TAGGING")
c.execute("SELECT account, COUNT(*) FROM trades WHERE pnl IS NOT NULL GROUP BY account")
tags = c.fetchall()
for row in tags:
    print("  " + str(row[0]) + ": " + str(row[1]) + " trades")
if any(r[0] and 'Live' in str(r[0]) for r in tags):
    print("  [OK] Live account trades tagged")
elif v3_t > 0:
    print("  [INFO] Live trades will be tagged on close")

# 8. Open Positions
print("\n8. OPEN POSITIONS")
for a in config['accounts']:
    if a.get('enabled'):
        try:
            mt5.login(a['account'], password='', server=a['server'])
            pos = mt5.positions_get()
            if pos:
                for p in pos:
                    print("  " + a['name'] + ": " + p.symbol + " " + ('BUY' if p.type==0 else 'SELL') + " @ " + str(round(p.price_open,5)) + " PnL=" + str(round(p.profit,2)))
        except:
            pass

conn.close()
mt5.shutdown()

print("\n" + "=" * 55)
print("  SYSTEM STATUS: " + ("ALL SYSTEMS GO" if all_ok else "NEEDS ATTENTION"))
print("=" * 55)
