"""EVIDENCE PIPELINE - Complete record for 90-day validation."""
import MetaTrader5 as mt5
import pandas as pd
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

class EvidencePipeline:
    """
    Complete evidence collection for 90-day paper trading.
    Every evaluation and trade fully documented.
    """
    
    def __init__(self):
        self.evidence_dir = Path("research/paper/V4_CANONICAL_1.0/evidence")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        
        self.evaluations_file = self.evidence_dir / "evaluations.jsonl"
        self.trades_file = self.evidence_dir / "trades.jsonl"
        self.summary_file = self.evidence_dir / "daily_summary.jsonl"
        
        self.strategy_version = "V4_CANONICAL_1.0"
        
    def generate_signal_id(self, timestamp: str) -> str:
        """Generate unique signal ID."""
        data = f"{self.strategy_version}_{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def record_evaluation(self, evaluation: dict) -> dict:
        """Record a complete evaluation with ALL fields."""
        
        timestamp = datetime.now(timezone.utc).isoformat()
        signal_id = self.generate_signal_id(timestamp)
        
        complete_record = {
            # Identity
            "signal_id": signal_id,
            "strategy_version": self.strategy_version,
            "timestamp_utc": timestamp,
            
            # Market data
            "symbol": "USDJPYm",
            "timeframe": "H4",
            "price": evaluation.get("price"),
            "atr": evaluation.get("atr"),
            "ema_50": evaluation.get("ema_50"),
            "ema_200": evaluation.get("ema_200"),
            "bias": evaluation.get("bias"),
            
            # FVG details
            "fvg_detected": evaluation.get("fvg_detected", False),
            "fvg_candle_1_high": evaluation.get("fvg_candle_1_high"),
            "fvg_candle_3_low": evaluation.get("fvg_candle_3_low"),
            "fvg_size": evaluation.get("fvg_size"),
            
            # Session
            "session": evaluation.get("session", "OTHER"),
            "current_hour_utc": datetime.now(timezone.utc).hour,
            
            # Decision
            "decision": evaluation.get("decision", "REJECT"),
            "reason": evaluation.get("reason", "UNKNOWN"),
            
            # Risk and trade parameters
            "direction": "BUY",
            "risk_percent": 0.25,
            "risk_fraction": 0.0025,
            "entry": evaluation.get("entry"),
            "sl": evaluation.get("sl"),
            "tp": evaluation.get("tp"),
            "rr_ratio": 2.0 if evaluation.get("sl") and evaluation.get("tp") else None,
        }
        
        # Save to evaluations file
        with open(self.evaluations_file, 'a') as f:
            f.write(json.dumps(complete_record) + '\n')
        
        return complete_record
    
    def record_paper_trade(self, trade: dict) -> dict:
        """Record a complete paper trade with entry/exit."""
        
        trade_id = f"TRADE_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        complete_trade = {
            # Identity
            "trade_id": trade_id,
            "signal_id": trade.get("signal_id"),
            "strategy_version": self.strategy_version,
            
            # Entry
            "entry_time_utc": trade.get("entry_time_utc"),
            "entry_price": trade.get("entry_price"),
            "sl": trade.get("sl"),
            "tp": trade.get("tp"),
            
            # Exit
            "exit_time_utc": trade.get("exit_time_utc"),
            "exit_price": trade.get("exit_price"),
            
            # Result
            "result": trade.get("result"),  # SL, TP, TIMEOUT
            "result_r": trade.get("result_r"),
            "pnl_r": trade.get("pnl_r"),
            
            # Quality metrics
            "mfe": trade.get("mfe"),  # Maximum Favorable Excursion
            "mae": trade.get("mae"),  # Maximum Adverse Excursion
            "duration_bars": trade.get("duration_bars"),
            "duration_hours": trade.get("duration_hours"),
            
            # Risk
            "risk_percent": 0.25,
            "risk_fraction": 0.0025,
        }
        
        # Save to trades file
        with open(self.trades_file, 'a') as f:
            f.write(json.dumps(complete_trade) + '\n')
        
        return complete_trade
    
    def record_daily_summary(self):
        """Record daily summary of activity."""
        evaluations_today = self.count_evaluations_today()
        trades_today = self.count_trades_today()
        
        summary = {
            "date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "strategy_version": self.strategy_version,
            "evaluations_today": evaluations_today,
            "trades_today": trades_today,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }
        
        with open(self.summary_file, 'a') as f:
            f.write(json.dumps(summary) + '\n')
        
        return summary
    
    def count_evaluations_today(self) -> int:
        """Count today's evaluations."""
        if not self.evaluations_file.exists():
            return 0
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        count = 0
        with open(self.evaluations_file, 'r') as f:
            for line in f:
                if line.strip() and today in line:
                    count += 1
        return count
    
    def count_trades_today(self) -> int:
        """Count today's paper trades."""
        if not self.trades_file.exists():
            return 0
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        count = 0
        with open(self.trades_file, 'r') as f:
            for line in f:
                if line.strip() and today in line:
                    count += 1
        return count
    
    def get_evidence_summary(self) -> dict:
        """Get complete evidence summary."""
        return {
            "strategy_version": self.strategy_version,
            "total_evaluations": self.count_total(self.evaluations_file),
            "total_trades": self.count_total(self.trades_file),
            "evaluations_today": self.count_evaluations_today(),
            "trades_today": self.count_trades_today(),
            "evidence_dir": str(self.evidence_dir)
        }
    
    def count_total(self, file_path: Path) -> int:
        """Count total lines in file."""
        if not file_path.exists():
            return 0
        with open(file_path, 'r') as f:
            return sum(1 for line in f if line.strip())
    
    def display_evidence_status(self):
        """Display evidence pipeline status."""
        summary = self.get_evidence_summary()
        
        print("="*70)
        print("  EVIDENCE PIPELINE STATUS")
        print("="*70)
        print(f"\n  Strategy: {summary['strategy_version']}")
        print(f"  Evidence directory: {summary['evidence_dir']}")
        print(f"\n  Total evaluations recorded: {summary['total_evaluations']}")
        print(f"  Total paper trades: {summary['total_trades']}")
        print(f"  Evaluations today: {summary['evaluations_today']}")
        print(f"  Trades today: {summary['trades_today']}")
        print(f"\n  Files:")
        print(f"    Evaluations: {self.evaluations_file.name}")
        print(f"    Trades: {self.trades_file.name}")
        print(f"    Daily summaries: {self.summary_file.name}")
        print("="*70)

if __name__ == "__main__":
    pipeline = EvidencePipeline()
    pipeline.display_evidence_status()
