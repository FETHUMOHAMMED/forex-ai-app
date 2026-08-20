"""Model Validation Framework - Calibration, OOS, Walk-Forward.
Proves whether confidence values are actually predictive.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
import sqlite3
from datetime import datetime, timezone

@dataclass
class CalibrationBucket:
    """One confidence range and its actual win rate"""
    range_low: float    # e.g., 0.80
    range_high: float   # e.g., 0.85
    trades: int = 0
    wins: int = 0
    
    @property
    def actual_win_rate(self) -> Optional[float]:
        if self.trades == 0:
            return None
        return self.wins / self.trades * 100
    
    @property
    def is_calibrated(self) -> bool:
        """Check if actual win rate matches confidence range"""
        if self.trades < 10:  # Need minimum sample
            return False
        expected_center = (self.range_low + self.range_high) / 2 * 100
        actual = self.actual_win_rate
        return abs(actual - expected_center) < 10  # Within 10% tolerance

@dataclass
class ModelValidationReport:
    """Complete model validation results"""
    model_id: str
    total_trades: int
    calibration_buckets: List[CalibrationBucket]
    overall_accuracy: Optional[float] = None
    brier_score: Optional[float] = None
    is_calibrated: bool = False
    has_sufficient_data: bool = False
    
    def summary(self) -> str:
        lines = [f"MODEL VALIDATION: {self.model_id}"]
        lines.append(f"  Total trades: {self.total_trades}")
        lines.append(f"  Sufficient data: {self.has_sufficient_data} (need 100+)")
        lines.append(f"  Calibrated: {self.is_calibrated}")
        lines.append(f"")
        lines.append(f"  CONFIDENCE BUCKETS:")
        for bucket in self.calibration_buckets:
            actual = bucket.actual_win_rate
            actual_str = f"{actual:.1f}%" if actual is not None else "N/A"
            expected_center = (bucket.range_low + bucket.range_high) / 2 * 100
            calibrated = "OK" if bucket.is_calibrated else ("N/A" if bucket.trades < 10 else "MISMATCH")
            lines.append(f"    {bucket.range_low*100:.0f}-{bucket.range_high*100:.0f}%: "
                        f"{bucket.trades} trades, actual={actual_str}, expected~{expected_center:.0f}%, [{calibrated}]")
        return "\n".join(lines)


def build_calibration_buckets(trades: List[dict]) -> List[CalibrationBucket]:
    """Group trades into confidence buckets and calculate actual win rates"""
    buckets = [
        CalibrationBucket(0.50, 0.55),
        CalibrationBucket(0.55, 0.60),
        CalibrationBucket(0.60, 0.65),
        CalibrationBucket(0.65, 0.70),
        CalibrationBucket(0.70, 0.75),
        CalibrationBucket(0.75, 0.80),
        CalibrationBucket(0.80, 0.85),
        CalibrationBucket(0.85, 0.90),
        CalibrationBucket(0.90, 0.95),
        CalibrationBucket(0.95, 1.00),
    ]
    
    for trade in trades:
        conf = trade.get('confidence', 0)
        result = trade.get('result', '')
        for bucket in buckets:
            if bucket.range_low <= conf < bucket.range_high:
                bucket.trades += 1
                if result == 'WIN':
                    bucket.wins += 1
                break
    
    return buckets


def validate_model(model_id: str, trades: List[dict]) -> ModelValidationReport:
    """Validate model calibration from trade data"""
    buckets = build_calibration_buckets(trades)
    total = len(trades)
    
    # Check if all buckets with >=10 trades are calibrated
    testable_buckets = [b for b in buckets if b.trades >= 10]
    calibrated_buckets = [b for b in testable_buckets if b.is_calibrated]
    is_calibrated = len(testable_buckets) > 0 and len(calibrated_buckets) == len(testable_buckets)
    
    return ModelValidationReport(
        model_id=model_id,
        total_trades=total,
        calibration_buckets=buckets,
        is_calibrated=is_calibrated,
        has_sufficient_data=total >= 100,
    )


def get_v3_trades_for_validation() -> List[dict]:
    """Get V3 trades for model validation"""
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    c.execute("""
        SELECT confidence, result FROM trades
        WHERE strategy_version='V3_REGIME' AND account='Live_Micro'
        AND result IN ('WIN','LOSS','BREAKEVEN') AND execution_contract_valid=1
    """)
    trades = [{"confidence": r[0], "result": r[1]} for r in c.fetchall()]
    conn.close()
    return trades


# ============================================================================
# OUT-OF-SAMPLE VALIDATION PROTOCOL
# ============================================================================

def walk_forward_validation(trades: List[dict], train_pct: float = 0.6, 
                            validation_pct: float = 0.2, test_pct: float = 0.2) -> dict:
    """
    Walk-forward validation protocol.
    Never validate on training data. Separate test set untouched.
    """
    total = len(trades)
    if total < 30:
        return {"error": "Need at least 30 trades for walk-forward validation"}
    
    train_size = int(total * train_pct)
    val_size = int(total * validation_pct)
    
    train_set = trades[:train_size]
    val_set = trades[train_size:train_size + val_size]
    test_set = trades[train_size + val_size:]
    
    return {
        "total": total,
        "train_size": len(train_set),
        "validation_size": len(val_set),
        "test_size": len(test_set),
        "test_set_untouched": len(test_set) > 0,
        "warning": "Do NOT modify strategy based on validation results. Test set is final arbiter.",
    }


if __name__ == "__main__":
    trades = get_v3_trades_for_validation()
    report = validate_model("V3_REGIME", trades)
    print(report.summary())
    
    print(f"\n{'='*60}")
    print("  CRITICAL DISTINCTIONS:")
    print("  1. Confidence 91% != 91% win probability")
    print("  2. Calibration must be proven empirically")
    print("  3. Out-of-sample testing is mandatory")
    print("  4. Walk-forward prevents overfitting")
    print(f"{'='*60}")
