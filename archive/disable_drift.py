with open("ai-service/auto_trader_exness.py","r",encoding="utf-8") as f:
    content = f.read()
content = content.replace('self.drift_pause_enabled = CONFIG.get("drift_pause_enabled", True)', 
                          'self.drift_pause_enabled = False  # Disabled for research mode')
with open("ai-service/auto_trader_exness.py","w",encoding="utf-8") as f:
    f.write(content)
print("Drift pause DISABLED")
