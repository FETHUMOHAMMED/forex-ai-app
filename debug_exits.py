"""Quick diagnostic – why aren't closed trades being logged?"""
import MetaTrader5 as mt5
from datetime import datetime, timezone
from trade_logger import TradeLogger

if not mt5.initialize():
    print("MT5 not running")
    exit()

# Connect to Demo2 (or your active account) – adjust login if needed
mt5.login(REDACTED_DEMO_ACCOUNT, password="REDACTED_DEMO2_PASSWORD", server="Exness-MT5Trial9")

# 1. Current open positions
positions = mt5.positions_get()
if positions:
    print(f"Open positions: {len(positions)}")
    for pos in positions:
        print(f"   Ticket {pos.ticket} {pos.symbol} {pos.type} vol={pos.volume} profit={pos.profit}")
else:
    print("No open positions (all trades are closed)")

# 2. Closed trades (history) – last 5
from_date = datetime(2026, 1, 1)
to_date = datetime.now()
history = mt5.history_deals_get(from_date, to_date)
if history and len(history) > 0:
    print(f"\nRecent deals (last 5):")
    for deal in history[-5:]:
        if deal.entry == mt5.DEAL_ENTRY_OUT:   # only exit deals
            print(f"   Ticket {deal.position_id} exit @ {deal.price} profit={deal.profit} time={datetime.fromtimestamp(deal.time, tz=timezone.utc)}")
else:
    print("No closed deals found in history.")

# 3. Database check
log = TradeLogger('trades.db')
pnls = log.get_recent_pnls(100)
print(f"\nDatabase closed trades with P&L: {len(pnls)}")