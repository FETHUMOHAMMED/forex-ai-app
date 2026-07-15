with open("ai-service/auto_trader_exness.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "# === VOLUME 6: Institutional Learning ==="
new = """# === VOLUME 6: Institutional Learning ===
            try:"""
content = content.replace(old, new)

old2 = 'if learn_result.recommendation == "SKIP":\n                logger.info(f"[LEARNING SKIP] {pair}: Historical performance suggests skipping")\n                continue'
new2 = 'if learn_result.recommendation == "SKIP":\n                    logger.info(f"[LEARNING SKIP] {pair}: Historical performance suggests skipping")\n                    continue\n            except Exception:\n                pass  # Learning engine optional for execution'
content = content.replace(old2, new2)

with open("ai-service/auto_trader_exness.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed - learning engine failure wont block execution")
