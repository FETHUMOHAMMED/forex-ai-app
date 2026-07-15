with open("ai-service/auto_trader_exness.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "            direction = signal['signal']"
new = """            direction = signal['signal']
            regime = signal.get('regime', 'volatile')

            # RULE 1: Require institutional score >= 55
            inst_score = signal.get('institutional_score', 0) or 0
            if inst_score < 55:
                logger.info(f"[INST REJECT] {pair}: Inst score {inst_score:.0f} < 55")
                continue

            # RULE 2: Reject counter-trend
            if regime == 'BULLISH' and direction == 'SELL':
                logger.info(f"[TREND REJECT] {pair}: H1 bullish, rejecting SELL")
                continue
            if regime == 'BEARISH' and direction == 'BUY':
                logger.info(f"[TREND REJECT] {pair}: H1 bearish, rejecting BUY")
                continue

            # RULE 3: Require liquidity event
            liquidity = signal.get('liquidity_state', 'NO_EVENT') or 'NO_EVENT'
            if 'NO_EVENT' in str(liquidity) or 'NO_LIQUIDITY' in str(liquidity):
                logger.info(f"[LIQ REJECT] {pair}: No liquidity event")
                continue

            # RULE 4: Block weak pairs
            blocked = ['USDCHF', 'USDSGD', 'NZDUSD', 'AUDUSD']
            if pair in blocked:
                continue

            # RULE 5: Require Grade A/B
            grade = signal.get('grade', 'F') or 'F'
            if grade in ('C', 'D', 'F'):
                logger.info(f"[GRADE REJECT] {pair}: Grade {grade} - not A/B")
                continue"""

if old in content:
    content = content.replace(old, new)
    print("All 5 rules applied")
else:
    print("Pattern not found")

with open("ai-service/auto_trader_exness.py", "w", encoding="utf-8") as f:
    f.write(content)
