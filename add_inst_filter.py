with open("ai-service/real_ai_service.py", "r", encoding="utf-8") as f:
    content = f.read()

old = """        return {
            'pair': pair,
            'signal': signal,
            'confidence': round(confidence, 3),"""

new = """        # RULE: Reject if institutional score < 55
        inst_score_check = inst_data.get('institutional_score', 0) if inst_data else 0
        if inst_score_check and inst_score_check < 55:
            return None

        return {
            'pair': pair,
            'signal': signal,
            'confidence': round(confidence, 3),"""

if old in content:
    content = content.replace(old, new)
    print("Inst<55 filter added to daemon")
else:
    print("Pattern not found")

with open("ai-service/real_ai_service.py", "w", encoding="utf-8") as f:
    f.write(content)
