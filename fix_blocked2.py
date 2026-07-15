with open("ai-service/real_ai_service.py", "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace("self.blocked_pairs = {'AUDUSD', 'USDCHF', 'USDSGD', 'NZDUSD'}", "self.blocked_pairs = {'AUDUSD'}")
with open("ai-service/real_ai_service.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Daemon: only AUDUSD blocked")
