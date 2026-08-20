content = open('frontend/src/App.js').read()

# Fix the V3 section with proper indentation
old = """      {/* SAFETY DOMINANT CARD */}
      <SafetyDominantCard
        signal={{ direction: 'SELL', confidence: 83 }}
        control={{ status: 'BLOCKED', reasons: ['STALE_SIGNAL (300s > 120s)', 'ENTRY_DEVIATION (41.9 pips > 5.0)', 'INVALID_SL (below entry for SELL)'] }}
        execution={{ status: 'NOT SENT' }}
      />
          <V3Performance data={v3Data.performance} />"""

new = """          {/* SAFETY DOMINANT CARD */}
          <SafetyDominantCard
            signal={{ direction: 'SELL', confidence: 83 }}
            control={{ status: 'BLOCKED', reasons: ['STALE_SIGNAL (300s > 120s)', 'ENTRY_DEVIATION (41.9 pips > 5.0)', 'INVALID_SL (below entry for SELL)'] }}
            execution={{ status: 'NOT SENT' }}
          />
          <V3Performance data={v3Data.performance} />"""

content = content.replace(old, new)
open('frontend/src/App.js', 'w').write(content)
print('Fixed JSX indentation')
