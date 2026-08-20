# Integrate RegimeStrategy into daemon V2
with open("ai-service/daemon_v2.py","r",encoding="utf-8") as f:
    content = f.read()

# Add regime strategy import
old_import = "from core.signal_pipeline_v2 import SignalPipelineV2 as SignalPipeline"
new_import = "from core.signal_pipeline_v2 import SignalPipelineV2 as SignalPipeline\nfrom core.regime_strategy import strategy as regime_strategy"
content = content.replace(old_import, new_import)

# Add regime filter after signal generation
old_append = 'signals.append(signal.to_dict())'
new_append = '''# Apply regime strategy filter
                    if regime_strategy.validate(signal):
                        signals.append(signal.to_dict())
                        logger.info(f"[SIGNAL] {pair} {signal.direction} conf={signal.confidence:.3f} inst={signal.institutional_score:.0f}")
                    else:
                        logger.debug(f"[REGIME REJECT] {pair}: {signal.rejection_reason}")'''

if old_append in content:
    content = content.replace(old_append, new_append)
    print("Regime strategy integrated into daemon V2")
else:
    print("Pattern not found - searching for signal append...")
    for i, line in enumerate(content.split('\n')):
        if 'signals.append' in line:
            print(f"  Line {i}: {line.strip()}")

with open("ai-service/daemon_v2.py","w",encoding="utf-8") as f:
    f.write(content)
