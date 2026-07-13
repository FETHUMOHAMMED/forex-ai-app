"""FOREX-AI-APP Institutional Intelligence Modules"""
from .market_microstructure import MarketMicrostructure, MicrostructureResult
from .trade_scorer import TradeScorer, TradeQualityScore, scorer
from .performance_tracker import InstitutionalPerformanceTracker

# Auto-snapshot every hour when imported
import threading
import time

def auto_snapshot():
    """Take performance snapshots every hour"""
    tracker = InstitutionalPerformanceTracker()
    while True:
        try:
            snap = tracker.take_snapshot()
            tracker.save_snapshot(snap)
        except:
            pass
        time.sleep(3600)  # 1 hour

# Start background snapshot thread
_snapshot_thread = threading.Thread(target=auto_snapshot, daemon=True)
_snapshot_thread.start()