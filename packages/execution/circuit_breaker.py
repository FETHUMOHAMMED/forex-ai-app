
"""Circuit breaker for MT5 connection failures"""
import time
from datetime import datetime, timezone
from enum import Enum

class CircuitState(str, Enum):
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Failing - block all orders
    HALF_OPEN = "HALF_OPEN" # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
        self.last_success_time = None
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def record_success(self):
        self.failure_count = 0
        self.last_success_time = datetime.now(timezone.utc)
        self.state = CircuitState.CLOSED
    
    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
            return False
        return True  # HALF_OPEN - allow one test order
    
    def reset(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
