"""Alerting Module - Slack/Telegram notifications for service status changes"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.heartbeat import Heartbeat
import json
from datetime import datetime, timezone
import time

class ServiceAlerter:
    """Monitors services and sends alerts on status changes"""
    
    def __init__(self, alert_interval=300):
        self.alert_interval = alert_interval  # Minimum seconds between alerts
        self.last_alert = {}  # service_name -> timestamp
        self.previous_status = {}  # service_name -> status
        self.heartbeat = Heartbeat("alerter")
    
    def send_alert(self, service_name, old_status, new_status):
        """Send alert about service status change"""
        now = time.time()
        
        # Rate limit alerts
        if service_name in self.last_alert:
            if now - self.last_alert[service_name] < self.alert_interval:
                return
        
        self.last_alert[service_name] = now
        
        # Determine emoji and severity
        if new_status == "OFFLINE" and old_status == "ONLINE":
            emoji = "??"
            severity = "CRITICAL"
            action = "WENT OFFLINE"
        elif new_status == "ONLINE" and old_status in ["OFFLINE", "STALE"]:
            emoji = "??"
            severity = "INFO"
            action = "CAME BACK ONLINE"
        elif new_status == "STALE":
            emoji = "??"
            severity = "WARNING"
            action = "HEARTBEAT STALE"
        else:
            emoji = "?"
            severity = "INFO"
            action = f"changed to {new_status}"
        
        title = f"{emoji} {service_name} {action}"
        message = f"Service: {service_name}\nOld Status: {old_status}\nNew Status: {new_status}\nTime: {datetime.now(timezone.utc).isoformat()}"
        
        # Try Slack
        try:
            from notify.slack_notifier import send_slack_message
            send_slack_message(f"*{title}*\n```{message}```")
            print(f"[ALERT Slack] {title}")
        except Exception as e:
            print(f"[ALERT] Slack failed: {e}")
        
        # Try Telegram
        try:
            from notify.telegram_notifier import send_telegram_message
            send_telegram_message(f"{title}\n\n{message}")
            print(f"[ALERT Telegram] {title}")
        except Exception as e:
            print(f"[ALERT] Telegram failed: {e}")
        
        # Always log to file
        log_file = Path("ai-service/service_alerts.jsonl")
        with open(log_file, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": service_name,
                "old_status": old_status,
                "new_status": new_status,
                "severity": severity
            }) + "\n")
    
    def check_services(self):
        """Check all services and alert on changes"""
        from tools.common import SERVICES, check_service
        
        for service_key, service_info in SERVICES.items():
            try:
                status_result = check_service(service_key)
                current_status = status_result["status"]
                
                # Get previous status
                prev = self.previous_status.get(service_key)
                
                if prev is not None and prev != current_status:
                    self.send_alert(service_info["name"], prev, current_status)
                
                self.previous_status[service_key] = current_status
            except Exception as e:
                print(f"[ALERT] Error checking {service_key}: {e}")
    
    def run(self, interval=60):
        """Run continuous monitoring"""
        print(f"[ALERTER] Starting service monitoring (interval: {interval}s)")
        self.heartbeat.start(interval_seconds=30)
        
        try:
            while True:
                self.check_services()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("[ALERTER] Stopped")
        finally:
            self.heartbeat.stop()

if __name__ == "__main__":
    alerter = ServiceAlerter()
    alerter.run()
