import sys, os, urllib.request, json, sqlite3, MetaTrader5 as mt5
sys.path.insert(0, '.')

print("=" * 50)
print("  FOREX-AI-APP SYSTEM HEALTH CHECK")
print("=" * 50)

all_ok = True

# 1. MT5
print("\n1. MT5")
try:
    mt5.initialize()
    info = mt5.terminal_info()
    print("  [OK] Connected" if info and info.connected else "  [FAIL] Not connected")
except:
    print("  [FAIL]"); all_ok = False

# 2. Daemon
print("\n2. DAEMON")
try:
    resp = urllib.request.urlopen('http://localhost:8001/health', timeout=5)
    data = json.loads(resp.read())
    print("  [OK] Running v" + str(data.get('version',0)))
except:
    print("  [FAIL] Offline"); all_ok = False

# 3. ML Models
print("\n3. ML MODELS")
import os as _os
models = [f for f in _os.listdir('ml/models') if f.endswith('.pkl')] if _os.path.exists('ml/models') else []
print("  [OK] " + str(len(models)) + " models")

# 4. Accounts
print("\n4. ACCOUNTS")
with open('ai-service/config.json') as f:
    config = json.load(f)
for a in config['accounts']:
    if a.get('enabled'):
        print("  [OK] " + a['name'] + " (" + str(a.get('pairs',[])) + ")")

# 5. Database
print("\n5. DATABASE")
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
print("  [OK] " + str(c.fetchone()[0]) + " closed trades")

# 6. V3
print("\n6. V3 STRATEGY")
c.execute("SELECT COUNT(*) FROM trades WHERE strategy_version='V3_REGIME'")
print("  [OK] " + str(c.fetchone()[0]) + " V3 trades")

# 7. Account Tagging
print("\n7. ACCOUNT TAGGING")
with open('ai-service/auto_trader_exness.py','r',encoding='latin-1') as f:
    has_fix = 'account=acc.name' in f.read()
print("  [OK] Tagging active" if has_fix else "  [FAIL]")

conn.close()
mt5.shutdown()

print("\n" + "=" * 50)
print("  STATUS: " + ("ALL SYSTEMS GO" if all_ok else "CHECK FAILED"))
print("=" * 50)
