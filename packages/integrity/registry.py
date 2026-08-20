"""Registry of all integrity checks"""
from typing import List, Callable
from .models import CheckResult

class CheckRegistry:
    def __init__(self):
        self.checks: List[Callable[[], CheckResult]] = []
    
    def register(self, check_fn):
        self.checks.append(check_fn)
        return check_fn
    
    def get_all(self):
        return self.checks

registry = CheckRegistry()
