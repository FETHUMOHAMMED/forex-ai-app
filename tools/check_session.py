import json
from datetime import datetime, timezone

# Load session config
with open('ai-service/config.json', 'r') as f:
    config = json.load(f)

session_hours = config.get('session_hours', {})
eurusd_hours = session_hours.get('EURUSD', [])

now = datetime.now(timezone.utc)
current_hour = now.hour
current_day = now.strftime('%A')

print(f"Current UTC time: {now}")
print(f"Current UTC hour: {current_hour}")
print(f"Current day: {current_day}")
print()
print(f"EURUSD session hours: {eurusd_hours}")

in_session = False
for start, end in eurusd_hours:
    if start <= end:
        if start <= current_hour < end:
            in_session = True
            print(f"  -> IN SESSION: {start}:00-{end}:00 UTC")
    else:
        if current_hour >= start or current_hour < end:
            in_session = True
            print(f"  -> IN SESSION: {start}:00-{end}:00 UTC (overnight)")

if not in_session:
    print(f"  -> OUTSIDE session hours")

# Check what day it considers
print(f"\nDay check: Monday=0, Tuesday=1, etc: {now.weekday()}")
