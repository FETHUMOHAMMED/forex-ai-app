"""Daily forward testing checklist."""
from datetime import datetime, timezone
import json
from pathlib import Path

def show_daily_checklist():
    """Show what needs to be done today."""
    now = datetime.now(timezone.utc)
    
    print("="*60)
    print(f"  DAILY CHECKLIST - {now.strftime('%Y-%m-%d')}")
    print("="*60)
    
    checklist = {
        "London Session Prep (6:30 UTC)": [
            "Check USDJPYm H4 chart",
            "Note current trend direction (EMA50 vs EMA200)",
            "Identify potential FVG zones",
            "Set price alerts for key levels"
        ],
        "London Session Active (7:00-11:00 UTC)": [
            "Run forward_test_engine.py every 15 minutes",
            "Document any FVG setups",
            "Record entry, SL, TP if setup appears",
            "Note market conditions (volatility, news)"
        ],
        "After Session (11:00 UTC)": [
            "Review any trades taken",
            "Check if trades followed strategy rules",
            "Update trade journal",
            "Calculate current forward test statistics"
        ],
        "End of Day (17:00 UTC)": [
            "Review all positions (if any open)",
            "Check for timeouts",
            "Record daily observations",
            "Plan for tomorrow's session"
        ]
    }
    
    for section, items in checklist.items():
        print(f"\n{section}:")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item}")
    
    print(f"\n{'='*60}")
    print(f"  KEY REMINDERS")
    print(f"{'='*60}")
    print("""
1. ONLY trade FVG setups (no other patterns)
2. ONLY during London session (7-11 UTC)
3. ONLY USDJPYm pair
4. ALWAYS use 2.5R target
5. NO EXCEPTIONS - follow the system exactly
""")

if __name__ == "__main__":
    show_daily_checklist()
