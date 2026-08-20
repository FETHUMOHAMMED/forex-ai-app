"""Alert deduplication - prevent flooding"""
import time
from collections import defaultdict

class AlertDeduplicator:
    def __init__(self, cooldown_seconds=300):
        self.cooldown = cooldown_seconds
        self.last_alert_time = defaultdict(float)
    
    def should_alert(self, alert_key: str) -> bool:
        now = time.time()
        if now - self.last_alert_time.get(alert_key, 0) > self.cooldown:
            self.last_alert_time[alert_key] = now
            return True
        return False
    
    def reset(self, alert_key: str):
        self.last_alert_time.pop(alert_key, None)
