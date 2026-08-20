"""Gate Hierarchy - 8 levels. Each level must pass before next.
Gate 0-5 fail = NO TRADE.
Gate 6 fail = trade excluded from research.
Gate 7 fail = validation-only mode.
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional

class GateLevel(str, Enum):
    GATE_0 = "SYSTEM_INTEGRITY"
    GATE_1 = "DATA_INTEGRITY"
    GATE_2 = "SIGNAL_INTEGRITY"
    GATE_3 = "EXECUTION_CONTRACT"
    GATE_4 = "RISK"
    GATE_5 = "MT5"
    GATE_6 = "TRADE_QUALIFICATION"
    GATE_7 = "STRATEGY_VALIDATION"

@dataclass
class GateResult:
    gate: GateLevel
    passed: bool
    action_if_failed: str
    detail: str = ""

class GateHierarchy:
    """The authoritative gate hierarchy."""
    
    def __init__(self):
        self.gate_results: Dict[GateLevel, GateResult] = {}
    
    def check_gate_0(self, domains: dict) -> GateResult:
        """SYSTEM INTEGRITY: All critical systems healthy"""
        required = ["api", "database", "mt5", "ai"]
        failures = [d for d in required if domains.get(d) != "PASS"]
        passed = len(failures) == 0
        return GateResult(GateLevel.GATE_0, passed, "NO TRADE",
                         f"Failures: {failures}" if failures else "All systems healthy")
    
    def check_gate_1(self, data: dict) -> GateResult:
        """DATA INTEGRITY: account, timestamps, provenance, schema, identity"""
        checks = [
            data.get("account_ok", False),
            data.get("timestamps_ok", False),
            data.get("provenance_ok", False),
            data.get("schema_ok", False),
            data.get("identity_ok", False),
        ]
        passed = all(checks)
        return GateResult(GateLevel.GATE_1, passed, "NO TRADE",
                         f"Passed {sum(checks)}/5 data checks")
    
    def check_gate_2(self, signal: dict) -> GateResult:
        """SIGNAL INTEGRITY: freshness, features, confidence, signal"""
        checks = [
            signal.get("fresh", False),
            signal.get("features_valid", False),
            signal.get("confidence_valid", False),
            signal.get("signal_valid", False),
        ]
        passed = all(checks)
        return GateResult(GateLevel.GATE_2, passed, "NO TRADE",
                         f"Passed {sum(checks)}/4 signal checks")
    
    def check_gate_3(self, execution: dict) -> GateResult:
        """EXECUTION CONTRACT: entry, deviation, SL, TP, spread"""
        checks = [
            execution.get("entry_valid", False),
            execution.get("deviation_ok", False),
            execution.get("sl_valid", False),
            execution.get("tp_valid", False),
            execution.get("spread_ok", False),
        ]
        passed = all(checks)
        return GateResult(GateLevel.GATE_3, passed, "NO TRADE",
                         f"Passed {sum(checks)}/5 execution checks")
    
    def check_gate_4(self, risk: dict) -> GateResult:
        """RISK: equity, budget, sizing, exposure, correlation"""
        checks = [
            risk.get("equity_ok", False),
            risk.get("budget_ok", False),
            risk.get("sizing_ok", False),
            risk.get("exposure_ok", False),
            risk.get("correlation_ok", False),
        ]
        passed = all(checks)
        return GateResult(GateLevel.GATE_4, passed, "NO TRADE",
                         f"Passed {sum(checks)}/5 risk checks")
    
    def check_gate_5(self, mt5: dict) -> GateResult:
        """MT5: account, position, order, exact reconciliation"""
        checks = [
            mt5.get("account_match", False),
            mt5.get("position_verified", False),
            mt5.get("order_verified", False),
            mt5.get("reconciled", False),
        ]
        passed = all(checks)
        return GateResult(GateLevel.GATE_5, passed, "NO TRADE",
                         f"Passed {sum(checks)}/4 MT5 checks")
    
    def check_gate_6(self, trade: dict) -> GateResult:
        """TRADE QUALIFICATION: closed, PnL, contract, reconciliation"""
        checks = [
            trade.get("closed", False),
            trade.get("pnl_valid", False),
            trade.get("contract_valid", False),
            trade.get("reconciled", False),
        ]
        passed = all(checks)
        return GateResult(GateLevel.GATE_6, passed, "EXCLUDE_FROM_RESEARCH",
                         f"Passed {sum(checks)}/4 qualification checks")
    
    def check_gate_7(self, trades_count: int, has_oos: bool, has_walkforward: bool) -> GateResult:
        """STRATEGY VALIDATION: 50+, 100+, 300+, OOS, walk-forward"""
        checks = [
            trades_count >= 50,
            trades_count >= 100,
            trades_count >= 300,
            has_oos,
            has_walkforward,
        ]
        passed = trades_count >= 300 and has_oos and has_walkforward
        return GateResult(GateLevel.GATE_7, passed, "VALIDATION_ONLY",
                         f"{trades_count} trades, OOS={has_oos}, WF={has_walkforward}")
    
    def run_all(self, domains=None, data=None, signal=None, execution=None,
                risk=None, mt5=None, trade=None, trades_count=0,
                has_oos=False, has_walkforward=False) -> Dict:
        """Run ALL gates in order. First failure blocks trading."""
        domains = domains or {}
        data = data or {}
        signal = signal or {}
        execution = execution or {}
        risk = risk or {}
        mt5 = mt5 or {}
        trade = trade or {}
        
        self.gate_results[GateLevel.GATE_0] = self.check_gate_0(domains)
        self.gate_results[GateLevel.GATE_1] = self.check_gate_1(data)
        self.gate_results[GateLevel.GATE_2] = self.check_gate_2(signal)
        self.gate_results[GateLevel.GATE_3] = self.check_gate_3(execution)
        self.gate_results[GateLevel.GATE_4] = self.check_gate_4(risk)
        self.gate_results[GateLevel.GATE_5] = self.check_gate_5(mt5)
        self.gate_results[GateLevel.GATE_6] = self.check_gate_6(trade)
        self.gate_results[GateLevel.GATE_7] = self.check_gate_7(trades_count, has_oos, has_walkforward)
        
        # Determine trading state (gates 0-5 must all pass)
        gates_0_to_5 = [GateLevel.GATE_0, GateLevel.GATE_1, GateLevel.GATE_2,
                        GateLevel.GATE_3, GateLevel.GATE_4, GateLevel.GATE_5]
        trading_allowed = all(self.gate_results[g].passed for g in gates_0_to_5)
        
        return {
            "trading_allowed": trading_allowed,
            "gate_results": {g.value: r.passed for g, r in self.gate_results.items()},
            "gate_details": {g.value: r.detail for g, r in self.gate_results.items()},
        }
    
    def print_hierarchy(self):
        """Print gate hierarchy status"""
        print("=" * 70)
        print("  GATE HIERARCHY")
        print("=" * 70)
        
        gate_names = {
            GateLevel.GATE_0: ("SYSTEM INTEGRITY", "NO TRADE if fails"),
            GateLevel.GATE_1: ("DATA INTEGRITY", "NO TRADE if fails"),
            GateLevel.GATE_2: ("SIGNAL INTEGRITY", "NO TRADE if fails"),
            GateLevel.GATE_3: ("EXECUTION CONTRACT", "NO TRADE if fails"),
            GateLevel.GATE_4: ("RISK", "NO TRADE if fails"),
            GateLevel.GATE_5: ("MT5", "NO TRADE if fails"),
            GateLevel.GATE_6: ("TRADE QUALIFICATION", "EXCLUDE if fails"),
            GateLevel.GATE_7: ("STRATEGY VALIDATION", "VALIDATION ONLY if fails"),
        }
        
        for gate in GateLevel:
            result = self.gate_results.get(gate)
            gate_num = gate.value.replace("GATE_", "")
            if result:
                name, action = gate_names[gate]
                icon = "PASS" if result.passed else "FAIL"
                print(f"  [{icon}] GATE {gate_num}: {name}")
                print(f"       Action if fail: {action}")
                print(f"       Detail: {result.detail}")
            else:
                print(f"  [....] GATE {gate_num}: {gate_names[gate][0]}")
        print("=" * 70)


if __name__ == "__main__":
    hierarchy = GateHierarchy()
    
    # Test with current system state
    result = hierarchy.run_all(
        domains={"api": "PASS", "database": "PASS", "mt5": "PASS", "ai": "PASS",
                 "frontend": "PASS", "observability": "PASS"},
        data={"account_ok": True, "timestamps_ok": True, "provenance_ok": True,
              "schema_ok": True, "identity_ok": True},
        signal={"fresh": True, "features_valid": True, "confidence_valid": True,
                "signal_valid": True},
        execution={"entry_valid": True, "deviation_ok": True, "sl_valid": True,
                   "tp_valid": True, "spread_ok": True},
        risk={"equity_ok": False, "budget_ok": False, "sizing_ok": False,
              "exposure_ok": True, "correlation_ok": True},
        mt5={"account_match": True, "position_verified": True,
             "order_verified": True, "reconciled": True},
        trade={"closed": False, "pnl_valid": False, "contract_valid": False,
               "reconciled": False},
        trades_count=0, has_oos=False, has_walkforward=False,
    )
    
    hierarchy.print_hierarchy()
    print(f"\n  TRADING ALLOWED: {result['trading_allowed']}")
