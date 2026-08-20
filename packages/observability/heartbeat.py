"""Heartbeat Module - Used by all services for health monitoring"""
import json
from pathlib import Path
from datetime import datetime, timezone
import threading
import time
import os

class Heartbeat:
    """Writes heartbeat files for service monitoring"""
    
    def __init__(self, service_name, heartbeat_file=None):
        self.service_name = service_name
        if heartbeat_file is None:
            root = Path(__file__).resolve().parent.parent.parent
            safe_name = service_name.lower().replace(" ", "_")
            self.heartbeat_file = root / "ai-service" / f"{safe_name}_heartbeat.json"
        else:
            self.heartbeat_file = Path(heartbeat_file)
        
        self._stop_event = threading.Event()
        self._thread = None
    
    def write_heartbeat(self, extra_data=None):
        """Write a single heartbeat"""
        data = {
            "service": self.service_name,
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "status": "running"
        }
        if extra_data:
            data.update(extra_data)
        
        self.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.heartbeat_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def start(self, interval_seconds=30, extra_data_func=None):
        """Start automatic heartbeat writing in background thread"""
        def _heartbeat_loop():
            while not self._stop_event.is_set():
                extra = extra_data_func() if extra_data_func else None
                self.write_heartbeat(extra)
                self._stop_event.wait(interval_seconds)
        
        self._thread = threading.Thread(target=_heartbeat_loop, daemon=True)
        self._thread.start()
        return self
    
    def stop(self):
        """Stop heartbeat writing"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        
        self.write_heartbeat({"status": "stopped"})


def quick_heartbeat(service_name, extra_data=None):
    """One-line heartbeat write"""
    hb = Heartbeat(service_name)
    hb.write_heartbeat(extra_data)


def classify_heartbeat(age_seconds):
    """
    Classify heartbeat age into health status
    
    Professional trading system thresholds:
      0-120s   = HEALTHY (normal operation)
      120-300s = WARNING (delayed, investigate)
      >300s    = STALE (possible issue)
      None     = OFFLINE (no heartbeat file)
    """
    if age_seconds is None:
        return "OFFLINE", "??"
    elif age_seconds <= 120:
        return "HEALTHY", "??"
    elif age_seconds <= 300:
        return "WARNING", "??"
    else:
        return "STALE", "??"


def get_heartbeat_status(service_name):
    """Get comprehensive heartbeat status for a service"""
    safe_name = service_name.lower().replace(" ", "_")
    hb_file = Path(f"ai-service/{safe_name}_heartbeat.json")
    
    if not hb_file.exists():
        return {
            "status": "OFFLINE",
            "icon": "??",
            "age_seconds": None,
            "last_heartbeat": None,
            "pid": None
        }
    
    try:
        with open(hb_file, 'r') as f:
            data = json.load(f)
            last_hb = datetime.fromisoformat(data['last_heartbeat'])
            now = datetime.now(timezone.utc)
            age = int((now - last_hb).total_seconds())
            status, icon = classify_heartbeat(age)
            
            return {
                "status": status,
                "icon": icon,
                "age_seconds": age,
                "last_heartbeat": data['last_heartbeat'],
                "pid": data.get('pid')
            }
    except:
        return {
            "status": "ERROR",
            "icon": "??",
            "age_seconds": None,
            "last_heartbeat": None,
            "pid": None
        }
