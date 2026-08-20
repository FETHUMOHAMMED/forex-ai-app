"""UPDATE CRITERIA - Flexible sample size per advisor."""
import json
from pathlib import Path

def update_criteria():
    """Update criteria with flexible sample size."""
    
    criteria_file = Path("research/paper/V4_CANONICAL_1.0/criteria.json")
    
    with open(criteria_file, 'r') as f:
        criteria = json.load(f)
    
    # Update sample requirements
    criteria["sample_requirements"] = {
        "min_trades": 50,
        "preferred_trades": 75,
        "duration_days": 90,
        "flexible_rule": "AT LEAST 50 trades AND 90 days, UNLESS strategy naturally produces fewer",
        "do_not_manufacture_trades": True,
        "market_controls_frequency": True
    }
    
    # Save updated criteria
    with open(criteria_file, 'w') as f:
        json.dump(criteria, f, indent=2)
    
    print("="*70)
    print("  CRITERIA UPDATED - FLEXIBLE SAMPLE SIZE")
    print("="*70)
    
    print(f"\n  Strategy: {criteria['strategy']}")
    print(f"  Frozen: {criteria['frozen']}")
    print(f"  Frozen Date: {criteria['frozen_date']}")
    
    print(f"\n  SAMPLE REQUIREMENTS (UPDATED):")
    print(f"    Min trades: {criteria['sample_requirements']['min_trades']}")
    print(f"    Preferred: {criteria['sample_requirements']['preferred_trades']}")
    print(f"    Duration: {criteria['sample_requirements']['duration_days']} days")
    print(f"    Rule: {criteria['sample_requirements']['flexible_rule']}")
    print(f"    Don't manufacture: {criteria['sample_requirements']['do_not_manufacture_trades']}")
    
    print(f"\n  KEY PRINCIPLE:")
    print(f"    The market controls trade frequency.")
    print(f"    The system must NOT force trades to hit targets.")
    print(f"    NO TRADE is a valid and correct outcome.")
    
    return criteria

if __name__ == "__main__":
    update_criteria()
