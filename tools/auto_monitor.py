"""Automated monitoring during London session."""
import time
from datetime import datetime, timezone
import subprocess
import json
from pathlib import Path

def auto_monitor():
    """Automatically check for setups during London session."""
    print("="*60)
    print("  AUTOMATED LONDON SESSION MONITOR")
    print("="*60)
    
    london_start = 7
    london_end = 11
    check_interval = 15 * 60  # 15 minutes in seconds
    
    print(f"  Monitoring from {london_start}:00 to {london_end}:00 UTC")
    print(f"  Check interval: {check_interval//60} minutes")
    print(f"  Press Ctrl+C to stop")
    print("="*60)
    
    try:
        while True:
            now = datetime.now(timezone.utc)
            
            # Check if in London session
            if london_start <= now.hour < london_end:
                print(f"\n[{now.strftime('%H:%M UTC')}] London session active - checking for setup...")
                
                # Run forward test engine
                result = subprocess.run(
                    [".\\ai-service\\venv\\Scripts\\python.exe", "tools/forward_test_engine.py"],
                    capture_output=True,
                    text=True
                )
                
                # Check output for setup
                if "Found setup" in result.stdout:
                    print("  SETUP FOUND!")
                    print(result.stdout)
                    
                    # Save alert
                    alert = {
                        "timestamp": now.isoformat(),
                        "type": "SETUP_FOUND",
                        "details": result.stdout
                    }
                    
                    alert_file = Path("research/forward_test/alerts.jsonl")
                    with open(alert_file, 'a') as f:
                        f.write(json.dumps(alert) + '\n')
                else:
                    print("  No setup found")
            
            else:
                if now.hour < london_start:
                    wait_hours = london_start - now.hour
                    print(f"\n[{(now + __import__('datetime').timedelta(hours=wait_hours)).strftime('%H:%M UTC')}] Next London session")
                else:
                    print(f"\n[Tomorrow 07:00 UTC] Next London session")
                
                # Sleep until next check (but not during non-London hours)
                time.sleep(check_interval)
                continue
            
            # Wait before next check
            time.sleep(check_interval)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    auto_monitor()
