with open("ai-service/real_ai_service.py","r",encoding="utf-8") as f:
    content = f.read()
content = content.replace("self.blocked_pairs = {'AUDUSD'}", "self.blocked_pairs = set()")
with open("ai-service/real_ai_service.py","w",encoding="utf-8") as f:
    f.write(content)
print("All pairs unblocked")
