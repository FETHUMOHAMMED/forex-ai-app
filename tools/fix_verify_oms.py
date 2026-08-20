content = open('tools/verify_oms.py').read()

old = '''for state, actor, reason in transitions:
    if not oms.transition(order_id, state, actor, "Live_Micro", "V3_REGIME", "Exness", reason):
        all_transitions_ok = False'''

new = '''for item in transitions:
    state = item[0]
    actor = item[1]
    reason = item[2]
    position_id = item[3] if len(item) > 3 else None
    if not oms.transition(order_id, state, actor, "Live_Micro", "V3_REGIME", "Exness", reason, position_id):
        all_transitions_ok = False'''

content = content.replace(old, new)
open('tools/verify_oms.py', 'w').write(content)
print('Fixed tuple unpacking')
