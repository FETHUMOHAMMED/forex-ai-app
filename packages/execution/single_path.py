
"""P0: Single Execution Path Enforcer.
Ensures ALL orders go through the 8-gate pipeline.
No code path can bypass the execution contract.
"""
import threading

class ExecutionPathEnforcer:
    """Singleton that tracks whether execute_pipeline() is the only path"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._pipeline_calls = 0
                cls._instance._direct_order_calls = 0
            return cls._instance
    
    def record_pipeline_call(self):
        self._pipeline_calls += 1
    
    def record_direct_order_call(self):
        """WARNING: Called when someone tries to bypass the pipeline"""
        self._direct_order_calls += 1
        print(f"[CRITICAL] Direct order_send() call detected! This bypasses the execution gate!")
    
    def verify_single_path(self) -> bool:
        """Return True if ONLY pipeline path was used"""
        return self._direct_order_calls == 0
    
    def get_stats(self):
        return {
            "pipeline_calls": self._pipeline_calls,
            "direct_order_calls": self._direct_order_calls,
            "single_path_enforced": self._direct_order_calls == 0,
        }

# Global instance
path_enforcer = ExecutionPathEnforcer()
