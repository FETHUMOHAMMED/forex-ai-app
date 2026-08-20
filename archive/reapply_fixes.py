with open("ai-service/auto_trader_exness.py","r",encoding="latin-1") as f:
    content = f.read()

# 1. SL multiplier
content = content.replace("'sl_atr_mult': 1.5", "'sl_atr_mult': 2.5")
content = content.replace("'tp_atr_mult': 2.5", "'tp_atr_mult': 4.0")
content = content.replace("params.get('sl_atr_mult', 1.5)", "params.get('sl_atr_mult', 2.5)")
content = content.replace("params.get('tp_atr_mult', 2.5)", "params.get('tp_atr_mult', 4.0)")

# 2. Account tagging
content = content.replace("acc.logger.log_trade_entry(signal, volume=lot_size, ticket=ticket, regime=regime)",
                          "acc.logger.log_trade_entry(signal, volume=lot_size, ticket=ticket, regime=regime, account=acc.name)")

# 3. Strength safe access
content = content.replace('signal["strength"]', 'signal.get("strength", "UNKNOWN")')

# 4. Regime and strength in debug log
content = content.replace("strength=None, regime=UNKNOWN",
                          'strength=signal.get("strength","UNKNOWN"), regime=signal.get("regime","UNKNOWN")')

# 5. Effective min confidence from config
content = content.replace("effective_min_conf = min_conf  # Use config value",
                          "effective_min_conf = min_conf  # Use config value")

with open("ai-service/auto_trader_exness.py","w",encoding="latin-1") as f:
    f.write(content)
print("All critical fixes reapplied")
