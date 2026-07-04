"""One‑off script to extract pair‑specific regime thresholds and save them to JSON."""
import json
from evolve_regime_params import build_regime_maps, PAIRS

if __name__ == '__main__':
    regime_maps = build_regime_maps()
    thresholds = {}
    for pair in PAIRS:
        key = pair + '_thresholds'
        if key in regime_maps:
            thresholds[pair] = regime_maps.pop(key)
    with open('regime_thresholds.json', 'w') as f:
        json.dump(thresholds, f, indent=2)
    print("✅ regime_thresholds.json created.")