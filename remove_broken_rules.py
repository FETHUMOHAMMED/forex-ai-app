with open("ai-service/auto_trader_exness.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove Rules 1, 3, 5 (they check fields not in signal cache)
# Keep only Rule 2 (trend alignment) which uses 'regime' field that IS in cache

old = """            # RULE 1: Require institutional score >= 55
            inst_score = signal.get('institutional_score', 0) or 0
            if inst_score < 55:
                logger.info(f"[INST REJECT] {pair}: Inst score {inst_score:.0f} < 55")
                continue

            # RULE 2: Reject counter-trend"""

new = """            # RULE 2: Reject counter-trend"""
content = content.replace(old, new)

old2 = """            # RULE 3: Require liquidity event
            liquidity = signal.get('liquidity_state', 'NO_EVENT') or 'NO_EVENT'
            if 'NO_EVENT' in str(liquidity) or 'NO_LIQUIDITY' in str(liquidity):
                logger.info(f"[LIQ REJECT] {pair}: No liquidity event")
                continue

# RULE 4: Removed - expanded pairs for data collection

            # RULE 5: Require Grade A/B
            grade = signal.get('grade', 'F') or 'F'
            if grade in ('C', 'D', 'F'):
                logger.info(f"[GRADE REJECT] {pair}: Grade {grade} - not A/B")
                continue"""
new2 = "# RULE 4: Removed - expanded pairs for data collection"
content = content.replace(old2, new2)

with open("ai-service/auto_trader_exness.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Removed Rules 1, 3, 5. Kept only Rule 2 (trend alignment).")
