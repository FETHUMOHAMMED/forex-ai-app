"""Simple rate limiting for API endpoints"""
import time
from collections import defaultdict
from fastapi import HTTPException

class RateLimiter:
    def __init__(self, max_requests=60, window_seconds=60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
    
    def check(self, client_ip: str):
        now = time.time()
        # Clean old requests
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window]
        
        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        self.requests[client_ip].append(now)
        return True

rate_limiter = RateLimiter()
