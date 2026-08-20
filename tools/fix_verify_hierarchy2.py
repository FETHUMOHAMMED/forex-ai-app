content = open('tools/verify_gate_hierarchy.py').read()

# Fix method name lookup to use gate number
old = '''    method_name = f"check_{gate.value.lower()}"
    if hasattr(GateHierarchy, method_name):'''

new = '''    gate_num = gate.value.replace("GATE_", "")
    method_name = f"check_gate_{gate_num}"
    if hasattr(GateHierarchy, method_name):'''

content = content.replace(old, new)
open('tools/verify_gate_hierarchy.py', 'w').write(content)
print('Fixed method lookup')
