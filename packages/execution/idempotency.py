"""Idempotency key for order submission - prevents duplicate orders"""
import hashlib
import time

class IdempotencyTracker:
    def __init__(self):
        self.processed_keys = {}
    
    def check_key(self, idempotency_key: str) -> bool:
        """Return True if this key has NOT been processed yet"""
        if idempotency_key in self.processed_keys:
            return False
        self.processed_keys[idempotency_key] = time.time()
        return True
    
    def cleanup(self, max_age_seconds=3600):
        now = time.time()
        expired = [k for k, t in self.processed_keys.items() if now - t > max_age_seconds]
        for k in expired:
            del self.processed_keys[k]

idempotency = IdempotencyTracker()
