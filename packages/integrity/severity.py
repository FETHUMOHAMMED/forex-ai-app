"""Severity levels for integrity checks"""
from enum import Enum

class Severity(str, Enum):
    CRITICAL = "CRITICAL"       # Failure = HALT trading
    WARNING = "WARNING"          # Failure = DEGRADED
    INFO = "INFO"                # Informational only
