with open("institutional/trade_scorer.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Lower min total score
content = content.replace("self.MIN_TOTAL_SCORE = 55", "self.MIN_TOTAL_SCORE = 50")

# Fix 2: Adjust ML scoring thresholds
old_ml = """        elif ml_conf >= 0.52:
            result.ml_score = 30
        else:
            result.ml_score = 15"""
new_ml = """        elif ml_conf >= 0.52:
            result.ml_score = 35
        elif ml_conf >= 0.50:
            result.ml_score = 25
        else:
            result.ml_score = 10"""
content = content.replace(old_ml, new_ml)

with open("institutional/trade_scorer.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed trade_scorer.py")
