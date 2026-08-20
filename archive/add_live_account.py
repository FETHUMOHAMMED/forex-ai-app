import json
with open("ai-service/config.json") as f:
    c = json.load(f)

# Check if Live_Micro already exists
exists = False
for a in c["accounts"]:
    if a["name"] == "Live_Micro":
        exists = True
        print("Live_Micro already exists")
        break

if not exists:
    live = {
        "name": "Live_Micro",
        "broker": "Exness",
        "account": 0,
        "server": "Exness-MT5Trial9",
        "enabled": False,
        "pairs": ["EURUSD", "GBPUSD"],
        "min_confidence": 0.50,
        "risk_percent": 0.01,
        "max_daily_trades": 5,
        "max_daily_loss_percent": 5.0,
        "trail_drawdown_percent": 5.0,
        "sessions_enabled": ["LONDON"],
        "loss_streak_reduce_enabled": True,
        "loss_streak_threshold": 3,
        "loss_streak_risk_multiplier": 0.5,
        "hedge_mode_enabled": False,
        "trail_atr_mult": 1.0,
        "break_even_atr_mult": 1.0,
        "enable_partial_close": False,
        "atr_min_jpy": 0.05,
        "atr_max_jpy": 0.5,
        "atr_min_non_jpy": 0.0005,
        "atr_max_non_jpy": 0.008
    }
    c["accounts"].append(live)
    with open("ai-service/config.json", "w") as f:
        json.dump(c, f, indent=2)
    print("Live_Micro account added (DISABLED - set enabled=true when ready)")
