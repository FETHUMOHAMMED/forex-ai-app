content = open('packages/strategy/signal_contract.py').read()

# Fix: accept lowercase regime values by converting to uppercase
old = '''    regime = ai_output.get("regime", "UNKNOWN")
    
    # UNKNOWN regime = REJECT
    if regime in ("UNKNOWN", None, ""):
        raise ValueError(f"UNKNOWN regime - cannot execute")'''

new = '''    regime = ai_output.get("regime", "UNKNOWN")
    
    # Normalize: lowercase -> uppercase (volatile -> VOLATILE)
    if isinstance(regime, str):
        regime = regime.upper()
    
    # UNKNOWN regime = REJECT
    if regime in ("UNKNOWN", None, ""):
        raise ValueError(f"UNKNOWN regime - cannot execute")'''

content = content.replace(old, new)
open('packages/strategy/signal_contract.py', 'w').write(content)
print('Fixed regime case normalization')
