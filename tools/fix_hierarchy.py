content = open('packages/integrity/gate_hierarchy.py').read()

old = '''        # Determine trading state
        gates_0_to_5 = [self.gate_results[g] for g in GateLevel if g.value <= "MT5"]
        trading_allowed = all(g.passed for g in gates_0_to_5 if g in self.gate_results)'''

new = '''        # Determine trading state (gates 0-5 must all pass)
        gates_0_to_5 = [GateLevel.GATE_0, GateLevel.GATE_1, GateLevel.GATE_2,
                        GateLevel.GATE_3, GateLevel.GATE_4, GateLevel.GATE_5]
        trading_allowed = all(self.gate_results[g].passed for g in gates_0_to_5)'''

content = content.replace(old, new)
open('packages/integrity/gate_hierarchy.py', 'w').write(content)
print('Fixed gate hierarchy bug')
