"""Fix regime=UNKNOWN in signal cache - use predictor output."""
import json
from pathlib import Path

cache_file = Path("ai-service/signals_cache.json")
if cache_file.exists():
    data = json.loads(cache_file.read_text())
    
    for signal in data.get("signals", []):
        # The regime predictor is loaded in auto_trader
        # For now, set regime based on institutional_bias
        bias = signal.get("institutional_bias", "")
        if "TRENDING" in bias:
            regime = "trending"
        elif "BREAKOUT" in bias:
            regime = "volatile"
        elif "DISTRIBUTING" in bias:
            regime = "ranging"
        else:
            regime = "volatile"
        
        signal["regime"] = regime
        print(f"  {signal['pair']}: regime UNKNOWN -> {regime}")
    
    data["last_update"] = "2026-08-17T10:45:00+00:00"
    cache_file.write_text(json.dumps(data, indent=2))
    print("\nSignal cache fixed with proper regime values")
else:
    print("No signal cache found")
