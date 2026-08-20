"""Update execution pipeline to use signal_entry vs actual_entry"""
content = open('packages/execution/execution_pipeline.py').read()

# The pipeline already calculates deviation and validates against actual fill
# Add explicit field tracking to the result
old_result = """    result = ExecutionPipelineResult(
        signal_id=signal.get('signal_id', 'unknown'),
        pair=signal.get('pair', ''),
        direction=signal.get('direction', ''),
    )"""

new_result = """    result = ExecutionPipelineResult(
        signal_id=signal.get('signal_id', 'unknown'),
        pair=signal.get('pair', ''),
        direction=signal.get('direction', ''),
    )
    
    # Explicit execution field separation
    result.signal_entry = signal.get('entry')
    result.requested_entry = signal.get('entry')
    result.actual_entry = freshness.current_entry if 'freshness' in dir() else None
    result.entry_deviation_pips = abs(result.actual_entry - result.signal_entry) * 10000 if result.actual_entry and result.signal_entry else 0"""

content = content.replace(old_result, new_result)

open('packages/execution/execution_pipeline.py', 'w').write(content)
print("Updated execution pipeline with explicit field separation")
