"""Scan Statistics - Written by daemon, read by live monitor"""
import json
from pathlib import Path
from datetime import datetime, timezone
import threading
import time

STATS_FILE = Path("ai-service/scan_stats.json")

class ScanStats:
    """Thread-safe scan statistics tracker"""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.reset_daily()
        self.load()
    
    def reset_daily(self):
        """Reset daily counters"""
        with self.lock:
            self.stats = {
                "last_scan_time": None,
                "pairs_scanned": [],
                "signals_generated_today": 0,
                "signals_passed_today": 0,
                "orders_today": 0,
                "rejections": {
                    "session": 0,
                    "confidence": 0,
                    "spread": 0,
                    "news": 0,
                    "regime": 0,
                    "structure": 0
                },
                "v3_trades_total": 0,
                "daily_limit": 2
            }
    
    def load(self):
        """Load existing stats from file"""
        if STATS_FILE.exists():
            try:
                with open(STATS_FILE, 'r') as f:
                    saved = json.load(f)
                    with self.lock:
                        self.stats.update(saved)
            except:
                pass
    
    def save(self):
        """Save stats to file"""
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATS_FILE, 'w') as f:
            with self.lock:
                data = self.stats.copy()
                data["last_scan_time"] = datetime.now(timezone.utc).isoformat()
            json.dump(data, f, indent=2)
    
    def record_scan(self, pairs_scanned, signals_found, signals_passed, rejections):
        """Record a scan cycle"""
        with self.lock:
            self.stats["last_scan_time"] = datetime.now(timezone.utc).isoformat()
            self.stats["pairs_scanned"] = pairs_scanned
            self.stats["signals_generated_today"] += signals_found
            self.stats["signals_passed_today"] += signals_passed
            for key, count in rejections.items():
                if key in self.stats["rejections"]:
                    self.stats["rejections"][key] += count
        self.save()
    
    def record_order(self):
        """Record a placed order"""
        with self.lock:
            self.stats["orders_today"] += 1
            self.stats["v3_trades_total"] += 1
        self.save()
    
    def get_stats(self):
        """Get current stats"""
        with self.lock:
            return self.stats.copy()


# Singleton instance
scan_stats = ScanStats()
