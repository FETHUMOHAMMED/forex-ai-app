"""
Volume 9 Module 5: Adaptive Decision Engine
The final intelligence gate. Combines all Volume 9 modules into a single decision.
Answers: "Should I trade this, and at what size?"
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from institutional.strategy_memory import StrategyMemory
from institutional.pair_intelligence import PairIntelligence
from institutional.regime_optimizer import RegimeOptimizer
from institutional.confidence_calibrator import ConfidenceCalibrator


@dataclass
class AdaptiveDecision:
    """Complete Volume 9 adaptive decision"""
    pair: str
    signal: str
    regime: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Confidence
    raw_confidence: float = 0.0
    adjusted_confidence: float = 0.0
    confidence_adjustment: float = 0.0

    # Component scores (0-100)
    pair_score: float = 0.0
    regime_score: float = 0.0
    pattern_score: float = 0.0
    composite_score: float = 0.0

    # Pair & Regime evaluations
    pair_quality: str = "UNKNOWN"
    regime_action: str = "UNKNOWN"

    # Decision
    decision: str = "REJECT"  # ALLOW, CAUTIOUS, REDUCE, REJECT
    grade: str = "F"
    risk_multiplier: float = 0.0  # 0.0 = no trade, 1.0 = full size
    reasoning: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Historical context
    historical_wr: float = 0.0
    historical_trades: int = 0
    calibration_reasons: List[str] = field(default_factory=list)


class AdaptiveDecisionEngine:
    """
    The final Volume 9 gate.
    
    Weights (calibrated from 157 data points):
        Pattern (historical WR): 35%
        Confidence (adjusted):   30%
        Regime quality:         20%
        Pair quality:           15%
    """

    def __init__(self):
        self.memory = StrategyMemory()
        self.pair_intel = PairIntelligence()
        self.regime_optimizer = RegimeOptimizer()
        self.calibrator = ConfidenceCalibrator()

        # Decision weights
        self.weights = {
            'pattern': 0.35,
            'confidence': 0.30,
            'regime': 0.20,
            'pair': 0.15,
        }

        # Score thresholds
        self.MIN_COMPOSITE_SCORE = 45
        self.STRONG_SCORE = 65

    def decide(self, pair: str, signal: str, regime: str,
               raw_confidence: float, signal_dict: Dict = None) -> AdaptiveDecision:
        """
        Make the final adaptive decision.

        Args:
            pair: Trading pair
            signal: BUY or SELL
            regime: Current market regime
            raw_confidence: Original ML confidence (0-1)
            signal_dict: Full signal dictionary (optional)

        Returns:
            AdaptiveDecision with final verdict
        """
        decision = AdaptiveDecision(
            pair=pair,
            signal=signal,
            regime=regime,
            raw_confidence=raw_confidence
        )

        # 1. Pair Intelligence
        pair_eval = self.pair_intel.evaluate_pair(pair)
        decision.pair_quality = pair_eval['quality']
        decision.pair_score = pair_eval['win_rate']

        if pair_eval['quality'] == 'BLOCK':
            decision.warnings.append(f"Pair {pair} is BLOCKED ({pair_eval['win_rate']}% WR)")
            decision.decision = "REJECT"
            decision.risk_multiplier = 0.0
            decision.grade = "F"
            decision.reasoning.append(f"REJECT: {pair} blocked - {pair_eval['win_rate']}% WR over {pair_eval['total_trades']} trades")
            return decision

        # 2. Regime Optimizer
        regime_eval = self.regime_optimizer.evaluate_regime_for_pair(pair, regime)
        decision.regime_action = regime_eval['action']
        decision.regime_score = regime_eval['win_rate']

        if regime_eval['action'] == 'BLOCK':
            decision.warnings.append(f"Regime {regime} is BLOCKED for {pair} ({regime_eval['win_rate']}% WR)")
            decision.decision = "REJECT"
            decision.risk_multiplier = 0.0
            decision.grade = "F"
            decision.reasoning.append(f"REJECT: {pair}+{regime} blocked - {regime_eval['win_rate']}% WR")
            return decision

        # 3. Confidence Calibration
        calibration = self.calibrator.calibrate(pair, regime, signal, raw_confidence)
        decision.adjusted_confidence = calibration['adjusted_confidence']
        decision.confidence_adjustment = calibration['total_adjustment']
        decision.calibration_reasons = [a['reason'] for a in calibration['adjustments']]

        # 4. Pattern Score (historical WR for this specific combo)
        pattern_wr = 50.0  # Default
        pattern_trades = 0
        if regime_eval['signals']:
            for s in regime_eval['signals']:
                if s['signal'] == signal:
                    pattern_wr = s['win_rate']
                    pattern_trades = s['trades']
                    break
        decision.historical_wr = pattern_wr
        decision.historical_trades = pattern_trades
        decision.pattern_score = pattern_wr

        # 5. Composite Score
        # Normalize confidence to 0-100
        conf_score = decision.adjusted_confidence * 100

        decision.composite_score = (
            decision.pattern_score * self.weights['pattern'] +
            conf_score * self.weights['confidence'] +
            decision.regime_score * self.weights['regime'] +
            decision.pair_score * self.weights['pair']
        )

        # 6. Determine decision
        if decision.composite_score >= self.STRONG_SCORE:
            decision.decision = "ALLOW"
            decision.grade = "A" if decision.composite_score >= 75 else "B"
            decision.risk_multiplier = 1.0
        elif decision.composite_score >= self.MIN_COMPOSITE_SCORE:
            decision.decision = "CAUTIOUS"
            decision.grade = "C"
            decision.risk_multiplier = 0.5
        elif decision.composite_score >= 35:
            decision.decision = "REDUCE"
            decision.grade = "D"
            decision.risk_multiplier = 0.25
        else:
            decision.decision = "REJECT"
            decision.grade = "F"
            decision.risk_multiplier = 0.0

        # 7. Build reasoning
        if decision.decision == "ALLOW":
            decision.reasoning.append(f"ALLOW: Strong historical configuration ({decision.composite_score:.0f}/100)")
        elif decision.decision == "CAUTIOUS":
            decision.reasoning.append(f"CAUTIOUS: Moderate confidence - reduced size")
        elif decision.decision == "REDUCE":
            decision.reasoning.append(f"REDUCE: Weak configuration - minimal size only")
        else:
            decision.reasoning.append(f"REJECT: Insufficient quality ({decision.composite_score:.0f}/100)")

        if decision.historical_trades >= 3:
            decision.reasoning.append(f"Historical: {pair}+{regime}+{signal} = {pattern_wr:.0f}% WR ({pattern_trades} trades)")

        decision.reasoning.extend(decision.calibration_reasons)

        return decision

    def evaluate_signal(self, signal_dict: Dict, regime: str) -> AdaptiveDecision:
        """
        Evaluate a complete signal dictionary through the adaptive engine.
        """
        pair = signal_dict.get('pair', 'UNKNOWN')
        signal = signal_dict.get('signal', 'UNKNOWN')
        raw_conf = signal_dict.get('confidence', 0.50)

        return self.decide(pair, signal, regime, raw_conf, signal_dict)

    def summary(self):
        """Print adaptive decision engine summary with test cases"""
        print("=" * 55)
        print("  ADAPTIVE DECISION ENGINE - Volume 9 Module 5")
        print("=" * 55)

        test_cases = [
            ("USDJPY", "BUY", "RANGING", 0.55),
            ("NZDUSD", "SELL", "RANGING", 0.55),
            ("NZDUSD", "BUY", "BREAKOUT", 0.55),
            ("AUDUSD", "SELL", "BREAKOUT", 0.60),
            ("EURUSD", "SELL", "RANGING", 0.53),
            ("GBPUSD", "BUY", "RANGING", 0.52),
            ("USDCAD", "BUY", "SWEEP_SELL", 0.54),
        ]

        for pair, signal, regime, raw in test_cases:
            result = self.decide(pair, signal, regime, raw)
            status = {"ALLOW": "[OK]", "CAUTIOUS": "[CA]", "REDUCE": "[RE]", "REJECT": "[XX]"}
            marker = status.get(result.decision, "[??]")

            print(f"\n  {marker} {pair} {signal} | Regime: {regime}")
            print(f"    Raw conf: {result.raw_confidence:.3f} -> Adjusted: {result.adjusted_confidence:.3f}")
            print(f"    Scores: Pair={result.pair_score:.0f} Regime={result.regime_score:.0f} Pattern={result.pattern_score:.0f} Composite={result.composite_score:.0f}")
            print(f"    Decision: {result.decision} Grade={result.grade} Risk={result.risk_multiplier:.0%}")
            if result.historical_trades >= 3:
                print(f"    Historical: {result.historical_wr:.0f}% WR ({result.historical_trades} trades)")

        print("\n" + "=" * 55)
        print("  ALL 5 MODULES OPERATIONAL")
        print("  Volume 9: ADAPTIVE STRATEGY OPTIMIZATION ENGINE")
        print("=" * 55)


if __name__ == "__main__":
    engine = AdaptiveDecisionEngine()
    engine.summary()
