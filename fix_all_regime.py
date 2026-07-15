with open("ai-service/auto_trader_exness.py", "r", encoding="utf-8") as f:
    content = f.read()

# Define regime variable before it's used - add after direction = signal['signal']
old = "            direction = signal['signal']"
new = "            direction = signal['signal']\n            regime = signal.get('regime', 'volatile')  # Default regime"

if old in content:
    content = content.replace(old, new)
    print("Added regime = signal.get('regime', 'volatile')")
else:
    print("direction = signal['signal'] not found")

with open("ai-service/auto_trader_exness.py", "w", encoding="utf-8") as f:
    f.write(content)
