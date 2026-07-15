with open("ai-service/auto_trader_exness.py", "r", encoding="utf-8") as f:
    content = f.read()
old = "            # RULE 4: Block weak pairs\n            blocked = ['USDCHF', 'USDSGD', 'NZDUSD', 'AUDUSD']\n            if pair in blocked:\n                continue"
content = content.replace(old, "# RULE 4: Removed - expanded pairs for data collection")
with open("ai-service/auto_trader_exness.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Rule 4 removed")
