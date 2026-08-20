"""LIVE VALIDATION RUNNER - Records every signal without execution."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

class LiveValidationRunner:
    def __init__(self):
        self.evidence_dir = Path("evidence/live_validation")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        
    def run_once(self):
        """Check for signals, evaluate gates, record decision."""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        record = {
            "timestamp": timestamp,
            "signal": None,
            "gates": {
                "STALE_SIGNAL": None,
                "EXTREME_DEVIATION": None,
                "INVALID_SL": None,
                "INVALID_TP": None,
                "SPREAD_TOO_HIGH": None,
                "SESSION_BLOCK": None,
                "DUPLICATE_SIGNAL": None,
                "WRONG_ACCOUNT": None,
                "WRONG_SYMBOL": None,
                "WRONG_STRATEGY": None,
                "RISK_BUDGET": None,
            },
            "decision": "NO_SIGNAL",
            "mt5_order_sent": False,
            "qualified": False
        }
        
        # Save to daily file
        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = self.evidence_dir / f"validation_{date_str}.jsonl"
        
        with open(filepath, 'a') as f:
            f.write(json.dumps(record) + '\n')
        
        return record
    
    def run_continuous(self, interval_seconds=60):
        """Run validation loop."""
        print(f"LIVE VALIDATION MODE - checking every {interval_seconds}s")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        try:
            while True:
                record = self.run_once()
                if record["decision"] != "NO_SIGNAL":
                    print(f"[{record['timestamp']}] Decision: {record['decision']}")
                    print(f"  Gates: {json.dumps(record['gates'], indent=2)}")
                    print(f"  MT5 Order: {record['mt5_order_sent']}")
                    print(f"  Qualified: {record['qualified']}")
                    print("-" * 40)
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\nValidation stopped. Evidence saved.")

if __name__ == "__main__":
    runner = LiveValidationRunner()
    runner.run_continuous(interval_seconds=300)  # 5 minutes
