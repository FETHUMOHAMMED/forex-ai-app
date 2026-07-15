with open("ai-service/auto_trader_exness.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "next_regime = self.predict_next_regime(pair, regime)"
new = 'next_regime = self.predict_next_regime(pair, signal.get("regime", "volatile"))'

if old in content:
    content = content.replace(old, new)
    print("Fixed")
else:
    print("Not found")

with open("ai-service/auto_trader_exness.py", "w", encoding="utf-8") as f:
    f.write(content)
