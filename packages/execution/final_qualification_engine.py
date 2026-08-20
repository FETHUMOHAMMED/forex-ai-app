"""Final Qualification Engine - Every gate reconstructed from IMMUTABLE evidence.
No None produces unexplained FAIL. Every FAIL has a REASON.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, List

@dataclass
class GateEvidence:
    """One gate check with complete evidence"""
    gate: str
    passed: bool
    reason: str = ""
    evidence: Dict = field(default_factory=dict)

class FinalQualificationEngine:
    """Qualifies trades from immutable evidence. No unexplained fails."""
    
    def qualify(self, trade: dict) -> Dict:
        """Complete qualification with evidence for every gate"""
        gates = []
        
        # === SIGNAL EVIDENCE ===
        signal_age = trade.get('signal_age_ms')
        if signal_age is None:
            gates.append(GateEvidence("signal_fresh", False, "RISK_DATA_MISSING",
                                    {"reason": "signal_age_ms is None"}))
        elif signal_age > 120000:
            gates.append(GateEvidence("signal_fresh", False, "STALE_SIGNAL",
                                    {"age_ms": signal_age, "max_ms": 120000}))
        else:
            gates.append(GateEvidence("signal_fresh", True, "OK",
                                    {"age_ms": signal_age}))
        
        # === ENTRY DEVIATION ===
        deviation = trade.get('entry_deviation_pips')
        if deviation is None:
            gates.append(GateEvidence("entry_deviation", False, "RISK_DATA_MISSING",
                                    {"reason": "entry_deviation_pips is None"}))
        elif abs(deviation) > 5.0:
            gates.append(GateEvidence("entry_deviation", False, "EXTREME_DEVIATION",
                                    {"deviation_pips": deviation, "max_pips": 5.0}))
        else:
            gates.append(GateEvidence("entry_deviation", True, "OK",
                                    {"deviation_pips": deviation}))
        
        # === SL VALIDATION ===
        direction = trade.get('signal')
        entry = trade.get('actual_entry') or trade.get('entry')
        sl = trade.get('actual_sl') or trade.get('stop_loss')
        
        if entry is None or sl is None:
            gates.append(GateEvidence("sl_valid", False, "SL_DATA_MISSING",
                                    {"entry": entry, "sl": sl}))
        else:
            sl_ok = sl > entry if direction == 'SELL' else sl < entry
            if sl_ok:
                gates.append(GateEvidence("sl_valid", True, "OK",
                                        {"entry": entry, "sl": sl, "direction": direction}))
            else:
                gates.append(GateEvidence("sl_valid", False, "SL_WRONG_SIDE",
                                        {"entry": entry, "sl": sl, "direction": direction}))
        
        # === TP VALIDATION ===
        tp = trade.get('actual_tp') or trade.get('take_profit')
        if entry is None or tp is None:
            gates.append(GateEvidence("tp_valid", False, "TP_DATA_MISSING",
                                    {"entry": entry, "tp": tp}))
        else:
            tp_ok = tp < entry if direction == 'SELL' else tp > entry
            if tp_ok:
                gates.append(GateEvidence("tp_valid", True, "OK",
                                        {"entry": entry, "tp": tp, "direction": direction}))
            else:
                gates.append(GateEvidence("tp_valid", False, "TP_WRONG_SIDE",
                                        {"entry": entry, "tp": tp, "direction": direction}))
        
        # === SPREAD ===
        spread = trade.get('spread_at_execution')
        if spread is None:
            gates.append(GateEvidence("spread_ok", False, "SPREAD_DATA_MISSING",
                                    {"reason": "spread_at_execution is None"}))
        elif spread > 0.0015:
            gates.append(GateEvidence("spread_ok", False, "SPREAD_TOO_HIGH",
                                    {"spread": spread, "max": 0.0015}))
        else:
            gates.append(GateEvidence("spread_ok", True, "OK",
                                    {"spread": spread}))
        
        # === RISK ===
        risk_budget = trade.get('risk_budget_usd')
        if risk_budget is None:
            gates.append(GateEvidence("risk_ok", False, "RISK_BUDGET_MISSING",
                                    {"reason": "risk_budget_usd is None"}))
        else:
            sl_pips = abs(entry - sl) / 0.0001 if entry and sl else 0
            actual_risk = sl_pips * 10.0 * (trade.get('volume') or 0.01)
            if actual_risk > risk_budget * 1.01:
                gates.append(GateEvidence("risk_ok", False, "RISK_BUDGET_EXCEEDED",
                                        {"actual_risk": actual_risk, "budget": risk_budget}))
            else:
                gates.append(GateEvidence("risk_ok", True, "OK",
                                        {"actual_risk": actual_risk, "budget": risk_budget}))
        
        # === MT5 POSITION ===
        mt5_pos = trade.get('mt5_position_id')
        if mt5_pos is None:
            gates.append(GateEvidence("mt5_position", False, "POSITION_MISSING",
                                    {"reason": "mt5_position_id is None"}))
        else:
            gates.append(GateEvidence("mt5_position", True, "OK",
                                    {"position": mt5_pos}))
        
        # === RECONCILIATION ===
        contract_valid = trade.get('execution_contract_valid', 0)
        pnl = trade.get('pnl')
        if contract_valid != 1:
            gates.append(GateEvidence("reconciled", False, "CONTRACT_INVALID",
                                    {"contract_valid": contract_valid}))
        elif pnl is None:
            gates.append(GateEvidence("reconciled", False, "PNL_MISSING",
                                    {"reason": "pnl is None"}))
        else:
            gates.append(GateEvidence("reconciled", True, "OK",
                                    {"pnl": pnl}))
        
        # === FINAL DECISION ===
        all_passed = all(g.passed for g in gates)
        failed_gates = [g for g in gates if not g.passed]
        
        return {
            "qualified": all_passed,
            "gates": gates,
            "failed_count": len(failed_gates),
            "failed_reasons": [f"{g.gate}: {g.reason}" for g in failed_gates],
        }


def print_final_qualification(trade_id: int):
    import sqlite3
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    c.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    row = c.fetchone()
    if not row:
        print(f"Trade {trade_id} not found")
        return
    cols = [d[0] for d in c.description]
    t = dict(zip(cols, row))
    conn.close()
    
    engine = FinalQualificationEngine()
    result = engine.qualify(t)
    
    print("=" * 70)
    print(f"  FINAL QUALIFICATION - ID {trade_id}")
    print(f"  (Every FAIL has explicit REASON + EVIDENCE)")
    print("=" * 70)
    
    for gate in result['gates']:
        icon = "PASS" if gate.passed else "FAIL"
        print(f"  [{icon}] {gate.gate}")
        print(f"       Reason: {gate.reason}")
        if gate.evidence:
            print(f"       Evidence: {gate.evidence}")
    
    print(f"\n  QUALIFIED: {'YES' if result['qualified'] else 'NO'}")
    if result['failed_reasons']:
        print(f"  Failed: {result['failed_count']} gates")
        for reason in result['failed_reasons']:
            print(f"    - {reason}")
    print("=" * 70)
    return result

if __name__ == "__main__":
    for tid in [163, 164]:
        print_final_qualification(tid)
        print()
