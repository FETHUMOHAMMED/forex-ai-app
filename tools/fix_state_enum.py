content = open('packages/integrity/state_transition_test.py').read()
content = content.replace('system_state = SystemState.RECONCILED', 'system_state = SystemState.RECONCILING')
open('packages/integrity/state_transition_test.py', 'w').write(content)
print('Fixed enum: RECONCILED -> RECONCILING')
