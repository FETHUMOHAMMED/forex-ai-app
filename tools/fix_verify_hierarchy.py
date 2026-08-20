content = open('tools/verify_gate_hierarchy.py').read()

# Fix: use direct gate value instead of split
old = '''    method_name = f"check_gate_{gate.value.split('_')[1].lower()}"
    if hasattr(GateHierarchy, method_name):'''

new = '''    method_name = f"check_{gate.value.lower()}"
    if hasattr(GateHierarchy, method_name):'''

content = content.replace(old, new)
open('tools/verify_gate_hierarchy.py', 'w').write(content)
print('Fixed method name check')
