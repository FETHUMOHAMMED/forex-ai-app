with open("ai-service/real_ai_service.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "self.blocked_pairs = {'AUDUSD', 'USDCHF', 'USDSGD'}"
new = "self.blocked_pairs = {'AUDUSD', 'USDCHF', 'USDSGD', 'NZDUSD'}"

if old in content:
    content = content.replace(old, new)
    print("NZDUSD added to blocked pairs")
else:
    print("Pattern not found")

with open("ai-service/real_ai_service.py", "w", encoding="utf-8") as f:
    f.write(content)
