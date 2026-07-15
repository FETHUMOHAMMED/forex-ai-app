with open("institutional/trade_scorer.py", "r", encoding="utf-8") as f:
    content = f.read()

old = 'result.recommendation = "SKIP"\n        elif result.total_score >= 40:'
new = 'result.recommendation = "CAUTIOUS"\n        elif result.total_score >= 40:'
content = content.replace(old, new)

with open("institutional/trade_scorer.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Grade D now = CAUTIOUS")
