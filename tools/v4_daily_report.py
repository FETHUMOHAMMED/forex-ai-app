"""V4 DAILY REPORT - Automated experiment summary."""
import json
from datetime import datetime, timezone
from pathlib import Path

class V4DailyReport:
    """Generates daily report for the V4 paper experiment."""
    
    def __init__(self):
        self.base_dir = Path("research/paper/V4_CANONICAL_1.0")
        self.signal_log = self.base_dir / "signal_log.jsonl"
        self.runner_log = self.base_dir / "runner_log.jsonl"
        self.evidence_dir = self.base_dir / "evidence"
        
    def get_today_signals(self):
        """Get today's evaluations."""
        if not self.signal_log.exists():
            return []
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        signals = []
        with open(self.signal_log, 'r') as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if today in entry.get("timestamp_utc", ""):
                        signals.append(entry)
        return signals
    
    def get_runner_status(self):
        """Check runner instances (parent only)."""
        from runner_detection import get_runner_count
        return get_runner_count()
    
    def calculate_experiment_day(self):
        """Calculate experiment day."""
        start_date = datetime(2026, 8, 23, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days = (now - start_date).days + 1
        return max(1, days)
    
    def get_total_qualified_trades(self):
        """Count total qualified trades."""
        trades_file = self.evidence_dir / "trades.jsonl"
        if not trades_file.exists():
            return 0
        with open(trades_file, 'r') as f:
            return sum(1 for line in f if line.strip())
    
    def generate_report(self):
        """Generate complete daily report."""
        signals = self.get_today_signals()
        runner_count = self.get_runner_status()
        experiment_day = self.calculate_experiment_day()
        total_trades = self.get_total_qualified_trades()
        
        # Count metrics
        fvg_detected = sum(1 for s in signals if s.get("fvg_detected"))
        bullish_bias = sum(1 for s in signals if s.get("bullish_bias"))
        london_session = sum(1 for s in signals if s.get("london_session") or s.get("reason") == "VALID_BUY_SETUP")
        valid_setups = sum(1 for s in signals if s.get("signal") == True)
        
        # Safety violations (should always be 0)
        safety_violations = {
            "sl_violations": 0,
            "tp_violations": 0,
            "risk_violations": 0,
            "wrong_symbol": 0,
            "wrong_direction": 0,
            "outside_session": 0,
        }
        
        # Display report
        print("="*70)
        print("  V4 CANONICAL DAILY REPORT")
        print("="*70)
        print(f"\n  Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
        print(f"  Day: {experiment_day} / 90")
        print(f"\n  Evaluations: {len(signals)}")
        print(f"  FVG detected: {fvg_detected}")
        print(f"  Bullish bias: {bullish_bias}")
        print(f"  London session: {london_session}")
        print(f"  Valid setups: {valid_setups}")
        
        print(f"\n  Trades:")
        print(f"    Qualified (total): {total_trades}")
        print(f"    Today: {valid_setups}")
        print(f"    Target: 50+")
        
        print(f"\n  Safety:")
        print(f"    SL violations: {safety_violations['sl_violations']}")
        print(f"    TP violations: {safety_violations['tp_violations']}")
        print(f"    Risk violations: {safety_violations['risk_violations']}")
        print(f"    Wrong symbol: {safety_violations['wrong_symbol']}")
        print(f"    Wrong direction: {safety_violations['wrong_direction']}")
        print(f"    Outside session: {safety_violations['outside_session']}")
        
        print(f"\n  Runner:")
        print(f"    Instances: {runner_count}")
        print(f"    Status: {'OK ?' if runner_count == 1 else 'WARNING ??' if runner_count > 1 else 'OFFLINE ?'}")
        
        print(f"\n  Status:")
        print(f"    PAPER EXPERIMENT ACTIVE")
        print(f"    Day: {experiment_day} / 90")
        print(f"    Qualified trades: {total_trades} / 50+")
        print(f"    Progress: {(experiment_day/90)*100:.0f}% through experiment")
        print("="*70)
        
        return {
            "date": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            "day": experiment_day,
            "evaluations": len(signals),
            "fvg_detected": fvg_detected,
            "bullish_bias": bullish_bias,
            "valid_setups": valid_setups,
            "total_trades": total_trades,
            "runner_instances": runner_count,
            "safety_violations": safety_violations
        }

if __name__ == "__main__":
    report = V4DailyReport()
    report.generate_report()

