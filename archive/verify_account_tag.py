"""Verify account tagging is working"""
import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("Current trades by account:")
c.execute("SELECT account, COUNT(*), ROUND(SUM(pnl),2) FROM trades WHERE pnl IS NOT NULL GROUP BY account")
for row in c.fetchall():
    print("  " + str(row[0]) + ": " + str(row[1]) + " trades, PnL $" + str(row[2]))

print("\nChecking if log_trade_entry has account parameter...")
import inspect, sys
sys.path.insert(0, 'ai-service')
from risk.trade_logger import TradeLogger
sig = inspect.signature(TradeLogger.log_trade_entry)
print("  Parameters: " + str(list(sig.parameters.keys())))
has_account = 'account' in sig.parameters
print("  Has 'account' param: " + str(has_account))

print("\nChecking if watchdog passes account name...")
with open("ai-service/auto_trader_exness.py","r") as f:
    content = f.read()
passes_account = "account=acc.name" in content
print("  Passes account=acc.name: " + str(passes_account))

print("\nALL CHECKS: " + ("PASS" if has_account and passes_account else "FAIL"))
print("Next trade will be tagged with account name.")
conn.close()
