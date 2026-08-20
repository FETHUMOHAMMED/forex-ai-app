"""Monitor trading sessions and alert when London is active."""
from datetime import datetime, timezone
import time

def monitor_sessions():
    """Monitor trading sessions."""
    print("="*60)
    print("  SESSION MONITOR")
    print("="*60)
    
    while True:
        now = datetime.now(timezone.utc)
        hour = now.hour
        minute = now.minute
        
        # Session definitions
        sessions = {
            "Sydney": (21, 6),
            "Tokyo": (0, 9),
            "London": (7, 11),
            "New York": (12, 16)
        }
        
        # Check which session is active
        active_sessions = []
        for name, (start, end) in sessions.items():
            if start <= hour < end:
                active_sessions.append(name)
        
        # Special: London/NY overlap (11-12 UTC)
        if hour == 11:
            active_sessions.append("OVERLAP")
        
        # Display status
        print(f"\r{' '*60}", end='')  # Clear line
        print(f"\r{now.strftime('%Y-%m-%d %H:%M UTC')} | Active: {', '.join(active_sessions) if active_sessions else 'None'}", end='')
        
        # Alert for London session
        if "London" in active_sessions:
            print(f"\n{'='*60}")
            print(f"  LONDON SESSION ACTIVE - CHECK FOR FVG SETUPS")
            print(f"{'='*60}")
            print(f"  Time: {now.strftime('%H:%M UTC')}")
            print(f"  Strategy: FVG_H4_2.5R_London")
            print(f"  Action: Run forward_test_engine.py to check for setups")
            print(f"{'='*60}\n")
            time.sleep(300)  # Wait 5 minutes before next alert
        else:
            time.sleep(60)  # Check every minute
        
        # Clear screen every hour for readability
        if minute == 0:
            print("\n" + "="*60)
            print(f"  HOURLY UPDATE - {now.strftime('%H:%M UTC')}")
            print("="*60)

if __name__ == "__main__":
    try:
        monitor_sessions()
    except KeyboardInterrupt:
        print("\n\nSession monitor stopped.")
