"""Watchdog Service - Auto-restart crashed services"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import check_service, SERVICES
from tools.heartbeat import Heartbeat
import time
import subprocess
import os
from datetime import datetime, timezone

# Watchdog configuration
WATCHDOG_CONFIG = {
    "check_interval": 30,  # seconds between checks
    "max_restart_attempts": 3,  # max restarts before alerting
    "restart_cooldown": 300,  # 5 minutes cooldown after max restarts
    "services": {
        "trading_daemon": {
            "start_command": ["cmd", "/c", "cd", "/d", "ai-service", "&&", ".\\venv\\Scripts\\python.exe", "auto_trader_exness.py"],
            "start_dir": "ai-service"
        },
        "backend_server": {
            "start_command": ["cmd", "/c", "cd", "/d", "backend", "&&", "node", "server.js"],
            "start_dir": "backend"
        }
    }
}

class Watchdog:
    def __init__(self):
        self.heartbeat = Heartbeat("watchdog")
        self.restart_history = {}  # service_name -> [(timestamp, success)]
        self.running = True
    
    def log(self, message):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[WATCHDOG {timestamp}] {message}")
        self.heartbeat.write_heartbeat({"last_action": message})
    
    def can_restart(self, service_name):
        """Check if we can restart this service (rate limiting)"""
        now = time.time()
        history = self.restart_history.get(service_name, [])
        
        # Remove old entries
        recent = [(t, s) for t, s in history if now - t < WATCHDOG_CONFIG["restart_cooldown"]]
        self.restart_history[service_name] = recent
        
        # Check if we've hit the limit
        failures = [s for t, s in recent if not s]
        if len(failures) >= WATCHDOG_CONFIG["max_restart_attempts"]:
            return False, f"Max restart attempts ({WATCHDOG_CONFIG['max_restart_attempts']}) reached in cooldown period"
        
        return True, "OK"
    
    def restart_service(self, service_name, service_config):
        """Attempt to restart a service"""
        can_restart, reason = self.can_restart(service_name)
        if not can_restart:
            self.log(f"? Cannot restart {service_name}: {reason}")
            self.send_alert(f"Watchdog: Cannot restart {service_name}", reason)
            return False
        
        self.log(f"?? Restarting {service_name}...")
        
        try:
            # Start the service
            start_dir = service_config.get("start_dir", ".")
            cmd = service_config["start_command"]
            
            subprocess.Popen(
                cmd,
                cwd=start_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            self.restart_history.setdefault(service_name, []).append((time.time(), True))
            self.log(f"? {service_name} restart command issued")
            return True
            
        except Exception as e:
            self.restart_history.setdefault(service_name, []).append((time.time(), False))
            self.log(f"? Failed to restart {service_name}: {e}")
            self.send_alert(f"Watchdog: Failed to restart {service_name}", str(e))
            return False
    
    def check_and_restart(self):
        """Check all services and restart if needed"""
        for service_name, service_config in WATCHDOG_CONFIG["services"].items():
            status = check_service(service_name)
            
            if status["status"] != "ONLINE":
                self.log(f"? {SERVICES[service_name]['name']} is {status['status']}")
                self.restart_service(service_name, service_config)
    
    def send_alert(self, title, message):
        """Send alert via available channels"""
        # Try Slack first
        try:
            from notify.slack_notifier import send_slack_message
            send_slack_message(f"?? *{title}*\n{message}")
            return
        except:
            pass
        
        # Try Telegram
        try:
            from notify.telegram_notifier import send_telegram_message
            send_telegram_message(f"?? {title}\n{message}")
            return
        except:
            pass
        
        # Fallback to log file
        log_file = Path("ai-service/watchdog_alerts.log")
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {title}: {message}\n")
    
    def run(self):
        """Main watchdog loop"""
        self.log("?? Watchdog started - monitoring services")
        self.heartbeat.start(interval_seconds=30)
        
        try:
            while self.running:
                self.check_and_restart()
                time.sleep(WATCHDOG_CONFIG["check_interval"])
        except KeyboardInterrupt:
            self.log("Watchdog stopped by user")
        finally:
            self.heartbeat.stop()
    
    def stop(self):
        self.running = False

if __name__ == "__main__":
    watchdog = Watchdog()
    watchdog.run()
