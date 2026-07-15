import json

# 1. Update config - pairs already narrowed to 4
with open("ai-service/config.json") as f:
    config = json.load(f)
for acc in config["accounts"]:
    if acc["name"] == "Demo2":
        acc["pairs"] = ["EURUSD", "USDCAD", "USDJPY", "GBPUSD"]
        acc["min_confidence"] = 0.53
        print("Rule 4: Pairs = " + str(acc["pairs"]))
with open("ai-service/config.json", "w") as f:
    json.dump(config, f, indent=2)

# 2. Update auto_trader_exness.py with rules 1,2,3,5
with open("ai-service/auto_trader_exness.py", "r", encoding="utf-8") as f:
    content = f.read()

# Rule 1: Require institutional score >= 55
old1 = "inst_score = quality.institutional_score"
new1 = """inst_score = quality.institutional_score
            # Rule 1: Reject if institutional score too low
            if inst_score < 55:
                logger.info(f"[INST REJECT] {pair}: Inst score {inst_score:.0f} < 55")
                continue"""
content = content.replace(old1, new1)

# Rule 2: Reject counter-trend
old2 = "# Phase 2: regime prediction risk adjustment"
new2 = """# Rule 2: Reject counter-trend trades
            h1_bias = signal.get('regime', 'volatile')
            if h1_bias == 'BULLISH' and direction == 'SELL':
                logger.info(f"[TREND REJECT] {pair}: H1 bullish, rejecting SELL")
                continue
            if h1_bias == 'BEARISH' and direction == 'BUY':
                logger.info(f"[TREND REJECT] {pair}: H1 bearish, rejecting BUY")
                continue

            # Phase 2: regime prediction risk adjustment"""
content = content.replace(old2, new2)

# Rule 3: Require liquidity event
old3 = "if signal['signal'] == 'BUY' and inst_bias == 'BEARISH' and inst_score < -20:"
new3 = """# Rule 3: Require liquidity event
            liquidity = signal.get('liquidity_state', 'NO_EVENT')
            if 'NO_EVENT' in str(liquidity) or 'NO_LIQUIDITY' in str(liquidity):
                logger.info(f"[LIQ REJECT] {pair}: No liquidity event detected")
                continue

            if signal['signal'] == 'BUY' and inst_bias == 'BEARISH' and inst_score < -20:"""
content = content.replace(old3, new3)

# Rule 5: Grade A/B execute, C shadow only, D/F reject
old5 = "if quality.recommendation == \"SKIP\":"
new5 = """# Rule 5: Grade C = shadow only
            if quality.grade == 'C':
                logger.info(f"[GRADE SHADOW] {pair}: Grade C - shadow only, no execution")
                continue

            if quality.recommendation == \"SKIP\":"""
content = content.replace(old5, new5)

with open("ai-service/auto_trader_exness.py", "w", encoding="utf-8") as f:
    f.write(content)

print("All 5 rules applied:")
print("  1. Institutional score >= 55 required")
print("  2. Counter-trend trades rejected")
print("  3. Liquidity event required")
print("  4. Only EURUSD, USDCAD, USDJPY, GBPUSD")
print("  5. Grade A/B execute, C shadow only, D/F reject")
