"""Prepare for tomorrow's London session."""
from datetime import datetime, timezone, timedelta

def prepare_for_tomorrow():
    """Show preparation checklist for tomorrow."""
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)
    
    print("="*60)
    print(f"  PREPARATION FOR TOMORROW ({tomorrow.strftime('%Y-%m-%d')})")
    print("="*60)
    
    print(f"\n  Target: London Session (07:00-11:00 UTC)")
    print(f"  Pair: USDJPYm")
    print(f"  Strategy: FVG_H4_2.5R_London")
    
    print(f"\n  PRE-SESSION CHECKLIST (06:30 UTC):")
    print(f"  ? Wake up and check MT5 connection")
    print(f"  ? Open USDJPYm H4 chart")
    print(f"  ? Check current trend (EMA50 vs EMA200)")
    print(f"  ? Note current price level")
    print(f"  ? Check for any upcoming news events")
    
    print(f"\n  DURING SESSION (07:00-11:00 UTC):")
    print(f"  ? Run forward_test_engine.py every 15 minutes")
    print(f"  ? Watch for FVG formation")
    print(f"  ? Document any setups in trade journal")
    print(f"  ? Do NOT trade other patterns")
    print(f"  ? Do NOT trade outside session")
    
    print(f"\n  KEY LEVELS TO WATCH:")
    print(f"  ? Recent H4 highs and lows")
    print(f"  ? Any unfilled FVGs from recent sessions")
    print(f"  ? Round numbers (154.00, 154.50, 155.00)")
    
    print(f"\n  REMINDERS:")
    print(f"  ? Only FVG entries")
    print(f"  ? Only London session")
    print(f"  ? Only USDJPYm")
    print(f"  ? SL = 2.0x ATR")
    print(f"  ? TP = 5.0x ATR (2.5R)")
    print(f"  ? Max hold = 50 bars")
    
    print(f"\n{'='*60}")

if __name__ == "__main__":
    prepare_for_tomorrow()
