import re

with open('real_ai_service.py', 'r') as f:
    content = f.read()

# Fix liquidity log line
old = 'logger.info(f"[LIQUIDITY] {pair}: nearest={liq_result.nearest_pool} "'
new = 'logger.info(f"[LIQUIDITY] {pair}: state={liq_result.liquidity_state} sweep={liq_result.sweep_detected} dir={liq_result.sweep_direction} "'
content = content.replace(old, new)

old = 'f"distance={liq_result.pool_distance_pips} "'
new = 'f"level={liq_result.nearest_liquidity} "'
content = content.replace(old, new)

old = 'f"sweep_prob={liq_result.sweep_probability:.0%} "'
new = 'f"strength={liq_result.sweep_strength:.2f} "'
content = content.replace(old, new)

old = 'f"inst_interest={liq_result.institutional_interest} "'
new = 'f"score={liq_result.liquidity_score:.0f}"'
content = content.replace(old, new)

# Fix structure log line
old = 'f"phase={struct_result.market_phase} "'
new = 'f"bias={struct_result.structure_bias} phase={struct_result.market_phase} "'
content = content.replace(old, new)

old = 'f"bias={struct_result.structure_bias} score={struct_result.structure_score:.0f} "'
new = 'f"score={struct_result.structure_score:.0f} "'
content = content.replace(old, new)

old = 'f"trend={struct_result.trend_quality} expansion={struct_result.expansion_state} "'
new = 'f"cont={struct_result.continuation_prob:.0%}"'
content = content.replace(old, new)

with open('real_ai_service.py', 'w') as f:
    f.write(content)

print('Fixed real_ai_service.py')
