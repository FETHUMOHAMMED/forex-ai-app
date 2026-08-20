"""P0: Enforce regime validation - UNKNOWN regime MUST reject trade."""
content = open('ai-service/auto_trader_exness.py', 'r', encoding='utf-8', errors='replace').read()

# Find where the signal enters execution pipeline and add regime check
old = '''[SIGNAL DEBUG] EURUSD: entering execution pipeline'''

# Add regime validation before execution
# The signal has regime=UNKNOWN but execution continues
# We need to check regime and reject if UNKNOWN

# Find the regime assignment in auto_trader
# Around line 1296: regime = signal.get('regime', 'volatile')
# But the signal actually has regime='UNKNOWN'

old_regime = "regime = signal.get('regime', 'volatile')  # Default regime"
new_regime = """# P0: Regime validation - UNKNOWN regime = REJECT
            regime = signal.get('regime', 'UNKNOWN')
            if regime == 'UNKNOWN' or regime is None:
                logger.info(f"REJECTED {pair}: UNKNOWN regime (acc={acc.name})")
                self.rejection_counts['regime'] = self.rejection_counts.get('regime', 0) + 1
                continue"""

if old_regime in content:
    content = content.replace(old_regime, new_regime)
    open('ai-service/auto_trader_exness.py', 'w', encoding='utf-8').write(content)
    print('Fixed: UNKNOWN regime now REJECTS trade')
else:
    print('Regime line not found - searching...')
    import re
    matches = re.findall(r'regime.*get.*regime.*volatile', content)
    for m in matches[:3]:
        print(f'  Found: {m.strip()[:80]}')
