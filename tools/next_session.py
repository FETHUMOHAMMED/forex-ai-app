"""Check current time and next London session."""
from datetime import datetime, timezone, timedelta

def check_next_session():
    """Calculate time until next London session."""
    now = datetime.now(timezone.utc)
    
    print("="*60)
    print("  CURRENT STATUS")
    print("="*60)
    print(f"  Current time: {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Current hour: {now.hour}:{now.minute:02d}")
    
    # London session is 7-11 UTC
    london_start = 7
    london_end = 11
    
    if london_start <= now.hour < london_end:
        print(f"\n  LONDON SESSION ACTIVE")
        print(f"  Time remaining: {london_end - now.hour - 1}h {60 - now.minute}m")
        print(f"  Action: Run forward_test_engine.py NOW")
    else:
        # Calculate next London session
        if now.hour < london_start:
            # Later today
            next_start = now.replace(hour=london_start, minute=0, second=0)
        else:
            # Tomorrow
            next_start = (now + timedelta(days=1)).replace(hour=london_start, minute=0, second=0)
        
        time_until = next_start - now
        hours = time_until.seconds // 3600
        minutes = (time_until.seconds % 3600) // 60
        
        print(f"\n  London session: INACTIVE")
        print(f"  Next session: {next_start.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Time until next session: {time_until.days}d {hours}h {minutes}m")
        
        if now.hour >= 17:
            print(f"\n  ACTION: Rest and prepare for tomorrow")
            print(f"  - Review today's notes")
            print(f"  - Check economic calendar for tomorrow")
            print(f"  - Ensure MT5 is ready")
        elif now.hour >= 11:
            print(f"\n  ACTION: Post-session review")
            print(f"  - Document any setups from today")
            print(f"  - Calculate running statistics")
            print(f"  - Plan for next session")
        else:
            print(f"\n  ACTION: Pre-session preparation")
            print(f"  - Check H4 chart")
            print(f"  - Note trend direction")
            print(f"  - Set alerts for potential FVG zones")
    
    print("="*60)

if __name__ == "__main__":
    check_next_session()
