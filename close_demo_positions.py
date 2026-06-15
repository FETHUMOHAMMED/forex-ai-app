"""
Automatically closes ALL open positions on Demo & Demo2 accounts.
Run once before going live with your $100 account.
"""

import json
import MetaTrader5 as mt5

CONFIG_PATH = "config.json"
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

# Pick the accounts you want to clean
accounts_to_clean = [acc for acc in config["accounts"] if acc["name"] in ("Demo", "Demo2")]

if not mt5.initialize():
    print("❌ MT5 not running. Please open MetaTrader 5 and try again.")
    exit()

for acc in accounts_to_clean:
    login = int(acc["account"])
    password = acc["password"]
    server = acc["server"]
    print(f"🔌 Logging into {acc['name']} …")

    if not mt5.login(login, password=password, server=server):
        print(f"   ❌ Login failed for {acc['name']}: {mt5.last_error()}")
        continue

    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        print(f"   ✅ No open positions on {acc['name']}")
    else:
        print(f"   🧹 Closing {len(positions)} positions …")
        for pos in positions:
            tick = mt5.symbol_info_tick(pos.symbol)
            if not tick:
                continue
            if pos.type == mt5.ORDER_TYPE_BUY:
                price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            else:
                price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": 234567,
                "comment": "Demo Cleanup",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"      ✅ {pos.symbol} {pos.volume} closed")
            else:
                print(f"      ❌ {pos.symbol} failed: {result.comment}")

    # Logout so we can log into the next account
    mt5.shutdown()
    mt5.initialize()

print("\n✅ All demo positions closed. You can now disable Demo/Demo2 in config.json.")