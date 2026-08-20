"""CANONICAL TRADE LEDGER - Single source of truth for all trade data."""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

class CanonicalTradeLedger:
    """
    THE ONLY trade ledger. Every analysis must consume this.
    Eliminates ALL inconsistencies between different analyses.
    """
    
    def __init__(self):
        self.ledger_dir = Path("research/paper/V4_CANONICAL_1.0")
        self.ledger_file = self.ledger_dir / "canonical_ledger.jsonl"
        
        # Frozen strategy definition (THE ONLY definition)
        self.strategy_definition = {
            "strategy_version": "V4_CANONICAL_1.0",
            "frozen_date": "2026-08-19",
            
            # Pair and direction (FROZEN)
            "pair": "USDJPYm",
            "direction": "BUY_ONLY",
            
            # Setup (FROZEN)
            "setup": "H4_BULLISH_FVG",
            "fvg_definition": "candle_1_high < candle_3_low",  # Explicit
            "bias": "BULLISH",
            "bias_definition": "EMA50 > EMA200",  # Explicit
            
            # Session (FROZEN - London only per advisor)
            "session": "LONDON",
            "session_start_utc": 7,
            "session_end_utc": 11,
            
            # Risk parameters (FROZEN - explicit)
            "sl_atr_mult": 2.0,
            "tp_atr_mult": 4.0,
            "rr_ratio": 2.0,
            "risk_percent": 0.25,  # NOT 25.0
            "risk_fraction": 0.0025,  # Explicit fraction
            "risk_units": "PERCENT_OF_EQUITY",  # Unambiguous
            
            # Execution (FROZEN)
            "max_hold_bars": 50,
            "entry_type": "MARKET",  # or LIMIT
            "timezone": "UTC",
            
            # Timestamp convention
            "all_timestamps_utc": True
        }
        
        # Save frozen definition
        definition_file = self.ledger_dir / "FROZEN_STRATEGY_DEFINITION.json"
        with open(definition_file, 'w') as f:
            json.dump(self.strategy_definition, f, indent=2)
    
    def log_trade(self, trade_data: Dict) -> Dict:
        """Log a trade with complete canonical fields."""
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "strategy_version": "V4_CANONICAL_1.0",
            
            # Trade identification
            "trade_id": trade_data.get("trade_id"),
            "signal_id": trade_data.get("signal_id"),
            
            # Strategy parameters (from frozen definition)
            "pair": self.strategy_definition["pair"],
            "direction": self.strategy_definition["direction"],
            "session": self.strategy_definition["session"],
            "rr_ratio": self.strategy_definition["rr_ratio"],
            "risk_percent": self.strategy_definition["risk_percent"],
            
            # Trade details
            "entry_price": trade_data.get("entry_price"),
            "sl_price": trade_data.get("sl_price"),
            "tp_price": trade_data.get("tp_price"),
            "exit_price": trade_data.get("exit_price"),
            
            # Outcome
            "r_multiple": trade_data.get("r_multiple"),
            "pnl_r": trade_data.get("pnl_r"),
            "result": trade_data.get("result"),  # SL, TP, TIMEOUT
            
            # Execution quality
            "planned_entry": trade_data.get("planned_entry"),
            "actual_entry": trade_data.get("actual_entry"),
            "slippage_pips": trade_data.get("slippage_pips", 0),
            "spread_at_entry": trade_data.get("spread_at_entry"),
            
            # MAE/MFE
            "mae_r": trade_data.get("mae_r"),
            "mfe_r": trade_data.get("mfe_r"),
            
            # Holding
            "entry_time_utc": trade_data.get("entry_time_utc"),
            "exit_time_utc": trade_data.get("exit_time_utc"),
            "bars_held": trade_data.get("bars_held"),
            
            # Reconciliation
            "reconciliation_status": trade_data.get("reconciliation_status", "PENDING")
        }
        
        with open(self.ledger_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return entry
    
    def log_signal(self, signal_data: Dict) -> Dict:
        """Log a signal (including NO_TRADE)."""
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "strategy_version": "V4_CANONICAL_1.0",
            
            # Signal decision
            "signal": signal_data.get("signal", False),
            "reason": signal_data.get("reason", "UNKNOWN"),
            
            # Conditions at time of check
            "pair": self.strategy_definition["pair"],
            "fvg_detected": signal_data.get("fvg_detected", False),
            "bullish_bias": signal_data.get("bullish_bias", False),
            "session_active": signal_data.get("session_active", False),
            "regime": signal_data.get("regime", "UNKNOWN"),
            "spread": signal_data.get("spread"),
            
            # Risk units (explicit)
            "risk_percent": self.strategy_definition["risk_percent"],
            "risk_fraction": self.strategy_definition["risk_fraction"],
        }
        
        signal_file = self.ledger_dir / "signal_log.jsonl"
        with open(signal_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return entry
    
    def get_frozen_definition(self) -> Dict:
        """Return frozen strategy definition."""
        return self.strategy_definition
    
    def verify_no_ambiguity(self) -> Dict:
        """Verify no ambiguous values exist."""
        checks = {
            "risk_percent_explicit": self.strategy_definition["risk_percent"] == 0.25,
            "risk_fraction_explicit": self.strategy_definition["risk_fraction"] == 0.0025,
            "direction_explicit": self.strategy_definition["direction"] == "BUY_ONLY",
            "session_explicit": self.strategy_definition["session"] == "LONDON",
            "rr_explicit": self.strategy_definition["rr_ratio"] == 2.0,
            "pair_explicit": self.strategy_definition["pair"] == "USDJPYm",
            "timestamps_utc": self.strategy_definition["all_timestamps_utc"] == True,
        }
        
        all_clear = all(checks.values())
        
        return {
            "all_clear": all_clear,
            "checks": checks
        }

if __name__ == "__main__":
    ledger = CanonicalTradeLedger()
    
    print("="*70)
    print("  CANONICAL TRADE LEDGER")
    print("="*70)
    
    # Verify no ambiguity
    verification = ledger.verify_no_ambiguity()
    
    print(f"\n  AMBIGUITY CHECK:")
    for check, passed in verification["checks"].items():
        status = "?" if passed else "?"
        print(f"    {status} {check}")
    
    print(f"\n  All clear: {verification['all_clear']}")
    
    # Show frozen definition
    definition = ledger.get_frozen_definition()
    print(f"\n  FROZEN STRATEGY DEFINITION:")
    print(f"    Pair: {definition['pair']}")
    print(f"    Direction: {definition['direction']}")
    print(f"    Session: {definition['session']} ({definition['session_start_utc']}-{definition['session_end_utc']} UTC)")
    print(f"    R:R: {definition['rr_ratio']}")
    print(f"    Risk: {definition['risk_percent']}% ({definition['risk_fraction']} fraction)")
    print(f"    Frozen: {definition['frozen_date']}")
