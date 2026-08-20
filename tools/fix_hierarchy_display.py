content = open('packages/integrity/gate_hierarchy.py').read()

# Fix the gate number display
old = '''        for gate in GateLevel:
            result = self.gate_results.get(gate)
            if result:
                name, action = gate_names[gate]
                icon = "PASS" if result.passed else "FAIL"
                print(f"  [{icon}] GATE {gate.value.split('_')[1]}: {name}")
                print(f"       Action if fail: {action}")
                print(f"       Detail: {result.detail}")
            else:
                print(f"  [....] GATE {gate.value.split('_')[1]}: {gate_names[gate][0]}")'''

new = '''        for gate in GateLevel:
            result = self.gate_results.get(gate)
            gate_num = gate.value.replace("GATE_", "")
            if result:
                name, action = gate_names[gate]
                icon = "PASS" if result.passed else "FAIL"
                print(f"  [{icon}] GATE {gate_num}: {name}")
                print(f"       Action if fail: {action}")
                print(f"       Detail: {result.detail}")
            else:
                print(f"  [....] GATE {gate_num}: {gate_names[gate][0]}")'''

content = content.replace(old, new)
open('packages/integrity/gate_hierarchy.py', 'w').write(content)
print('Fixed display')
