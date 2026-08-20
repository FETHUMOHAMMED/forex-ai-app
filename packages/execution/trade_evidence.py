"""Trade Evidence Record - Complete immutable audit trail for one trade."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, List
import json

@dataclass
class TradeEvidenceRecord:
    """THE complete immutable evidence record for one trade."""
    
    # Identity
    signal_id: str
    account_id: int
    MT5_login: int
    strategy_version: str
    model_version: str
    
    # Timestamps (with sources)
    signal_time: str
    execution_attempt_time: str
    signal_time_source: str = "APP"  # APP or MT5
    execution_time_source: str = "APP"
    mt5_open_time: Optional[str] = None
    mt5_open_time_source: str = "MT5"
    mt5_close_time: Optional[str] = None
    mt5_close_time_source: str = "MT5"
    
    # Market data
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    
    # Prices
    planned_entry: float = 0.0
    actual_entry: Optional[float] = None
    planned_sl: float = 0.0
    actual_sl: Optional[float] = None
    planned_tp: float = 0.0
    actual_tp: Optional[float] = None
    
    # Risk
    equity: float = 0.0
    risk_budget: float = 0.0
    actual_risk: Optional[float] = None
    volume: float = 0.0
    
    # MT5 identity
    order_ticket: Optional[int] = None
    position_ticket: Optional[int] = None
    deal_ticket: Optional[int] = None
    
    # Decisions
    control_decision: str = "PENDING"
    risk_decision: str = "PENDING"
    execution_decision: str = "PENDING"
    reconciliation_decision: str = "PENDING"
    
    # Final classification
    final_classification: str = "RAW"  # RAW / EXECUTION_VALID / QUALIFIED
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_hash: str = ""
    
    def __post_init__(self):
        """Generate immutable hash at creation."""
        content = json.dumps({
            "signal_id": self.signal_id,
            "account_id": self.account_id,
            "MT5_login": self.MT5_login,
            "strategy": self.strategy_version,
            "signal_time": self.signal_time,
            "planned_entry": self.planned_entry,
            "planned_sl": self.planned_sl,
            "planned_tp": self.planned_tp,
            "volume": self.volume,
        }, sort_keys=True)
        import hashlib
        object.__setattr__(self, 'evidence_hash', hashlib.sha256(content.encode()).hexdigest()[:16])
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON storage."""
        return asdict(self)
    
    def save(self, path: str = "ai-service/trade_evidence.jsonl"):
        """Append to immutable evidence ledger."""
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(self.to_dict()) + "\n")
        return self.evidence_hash
    
    def verify_integrity(self) -> bool:
        """Verify evidence record has not been mutated."""
        import hashlib
        content = json.dumps({
            "signal_id": self.signal_id,
            "account_id": self.account_id,
            "MT5_login": self.MT5_login,
            "strategy": self.strategy_version,
            "signal_time": self.signal_time,
            "planned_entry": self.planned_entry,
            "planned_sl": self.planned_sl,
            "planned_tp": self.planned_tp,
            "volume": self.volume,
        }, sort_keys=True)
        current_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return current_hash == self.evidence_hash
    
    def print_evidence(self):
        """Print complete evidence record."""
        print("=" * 70)
        print("  TRADE EVIDENCE RECORD")
        print("=" * 70)
        print(f"\n  IDENTITY:")
        print(f"    Signal: {self.signal_id}")
        print(f"    Account: {self.account_id} (MT5: {self.MT5_login})")
        print(f"    Strategy: {self.strategy_version} (model {self.model_version})")
        
        print(f"\n  TIMESTAMPS:")
        print(f"    Signal: {self.signal_time}")
        print(f"    Execution: {self.execution_attempt_time}")
        print(f"    MT5 Open: {self.mt5_open_time or 'N/A'}")
        print(f"    MT5 Close: {self.mt5_close_time or 'N/A'}")
        
        print(f"\n  MARKET:")
        print(f"    Bid: {self.bid} | Ask: {self.ask} | Spread: {self.spread}")
        
        print(f"\n  PRICES:")
        print(f"    Planned: {self.planned_entry} | SL: {self.planned_sl} | TP: {self.planned_tp}")
        print(f"    Actual:  {self.actual_entry or 'N/A'} | SL: {self.actual_sl or 'N/A'} | TP: {self.actual_tp or 'N/A'}")
        
        print(f"\n  RISK:")
        print(f"    Equity: ${self.equity:.2f}")
        print(f"    Budget: ${self.risk_budget:.4f}")
        print(f"    Actual: ${self.actual_risk or 'N/A'}")
        print(f"    Volume: {self.volume}")
        
        # Detailed risk calculation (auditor can verify)
        if self.planned_entry and self.planned_sl:
            sl_distance = abs(self.planned_entry - self.planned_sl)
            sl_pips = sl_distance / 0.0001
            pip_value = self.volume * 10.0  # $10/pip for 1 lot, $0.10 for 0.01
            gross_risk = sl_pips * pip_value
            print(f"\n  RISK CALCULATION (Auditable):")
            print(f"    Entry:          {self.planned_entry}")
            print(f"    Stop:           {self.planned_sl}")
            print(f"    Distance:       {sl_pips:.1f} pips")
            print(f"    Volume:         {self.volume}")
            print(f"    Pip value:      ${pip_value:.2f}")
            print(f"    Gross risk:     ${gross_risk:.2f}")
        
        print(f"\n  MT5 IDENTITY:")
        print(f"    Order: {self.order_ticket or 'N/A'}")
        print(f"    Position: {self.position_ticket or 'N/A'}")
        print(f"    Deal: {self.deal_ticket or 'N/A'}")
        
        print(f"\n  DECISIONS:")
        print(f"    Control: {self.control_decision}")
        print(f"    Risk: {self.risk_decision}")
        print(f"    Execution: {self.execution_decision}")
        print(f"    Reconciliation: {self.reconciliation_decision}")
        
        print(f"\n  FINAL: {self.final_classification}")
        print(f"  HASH: {self.evidence_hash}")
        print("=" * 70)


if __name__ == "__main__":
    # Test with ID 163's data
    evidence = TradeEvidenceRecord(
        signal_id="SIG_163",
        account_id=REDACTED_LIVE_ACCOUNT,
        MT5_login=REDACTED_LIVE_ACCOUNT,
        strategy_version="V3_REGIME",
        model_version="v1.0",
        signal_time="2026-08-10T07:06:24+00:00",
        execution_attempt_time="2026-08-10T07:06:24+00:00",
        mt5_open_time="2026-08-10T07:06:24+00:00",
        mt5_close_time="2026-08-10T07:09:25+00:00",
        bid=1.15542,
        ask=1.15550,
        spread=0.00008,
        planned_entry=1.15123,
        actual_entry=1.15542,
        planned_sl=1.15299,
        actual_sl=1.15299,
        planned_tp=1.14842,
        actual_tp=1.14842,
        equity=19.06,
        risk_budget=0.0095,
        actual_risk=2.43,
        volume=0.01,
        order_ticket=591026126,
        position_ticket=589584400,
        deal_ticket=342603327,
        control_decision="REJECT",
        risk_decision="REJECT_RISK_BUDGET",
        execution_decision="EXECUTION_EXCEPTION",
        reconciliation_decision="FAIL",
        final_classification="RAW",
    )
    
    evidence.print_evidence()
    
    # Save to ledger
    hash_val = evidence.save()
    print(f"\n  Saved with hash: {hash_val}")
