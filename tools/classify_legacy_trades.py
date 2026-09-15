"""CLASSIFY LEGACY TRADES - Mark V3 trades as PRE-V4."""
import json
from pathlib import Path

def classify_legacy_trades():
    """Mark all V3_REGIME trades as LEGACY_PRE_V4."""
    print("="*70)
    print("  CLASSIFY LEGACY TRADES")
    print("="*70)
    
    legacy_trades = [
        {"id": 146, "strategy": "V3_REGIME", "classification": "LEGACY_PRE_V4_PHANTOM"},
        {"id": 163, "strategy": "V3_REGIME", "classification": "LEGACY_PRE_V4_EXCEPTION"},
        {"id": 164, "strategy": "V3_REGIME", "classification": "LEGACY_PRE_V4_WIN"},
        {"id": 165, "strategy": "V3_REGIME", "classification": "LEGACY_PRE_V4_LOSS"},
    ]
    
    print(f"\n  Legacy trades to classify:")
    for trade in legacy_trades:
        print(f"    ID {trade['id']}: {trade['strategy']} ? {trade['classification']}")
    
    print(f"\n  These are PRE-V4 trades. They should NOT affect V4 statistics.")
    print(f"  V4 current trades: 0 (paper only)")
    print(f"  V4 qualified live trades: 0")
    
    return legacy_trades

if __name__ == "__main__":
    classify_legacy_trades()
