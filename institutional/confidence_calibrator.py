"""
Volume 9 Module 4: Confidence Calibrator
Converts raw AI confidence into historically-adjusted confidence.
Uses Pair Intelligence + Regime Optimizer + Strategy Memory.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import Dict, Tuple
from institutional.strategy_memory import StrategyMemory
from institutional.pair_intelligence import PairIntelligence
from institutional.regime_optimizer import RegimeOptimizer


class ConfidenceCalibrator:
    """
    Adjusts raw ML confidence based on historical evidence.
    
    Formula:
        adjusted = raw_confidence + pair_adj + regime_adj + pattern_bonus
        Capped at [0.25, 0.95]
    """

    def __init__(self):
        self.memory = StrategyMemory()
        self.pair_intel = PairIntelligence()
        self.regime_optimizer = RegimeOptimizer()
        
        # Weight factors
        self.pair_weight = 0.15
        self.regime_weight = 0.20
        self.pattern_weight = 0.25

    def calibrate(self, pair: str, regime: str, signal: str, raw_confidence: float) -> Dict:
        """
        Calibrate confidence based on all available historical data.
        
        Args:
            pair: Trading pair
            regime: Current market regime
            signal: BUY or SELL
            raw_confidence: Original ML confidence (0-1)
            
        Returns:
            Dict with adjusted confidence, adjustments, and reasoning
        """
        adjustments = []
        total_adjustment = 0.0

        # 1. Pair-level adjustment
        pair_eval = self.pair_intel.evaluate_pair(pair)
        pair_adj = pair_eval['confidence_adjustment'] / 100.0
        if pair_adj != 0:
            adjustments.append({
                'source': 'pair',
                'value': round(pair_adj, 3),
                'reason': f"Pair {pair_eval['quality']} ({pair_eval['win_rate']}% WR)"
            })
            total_adjustment += pair_adj * self.pair_weight

        # 2. Regime-level adjustment
        regime_eval = self.regime_optimizer.evaluate_regime_for_pair(pair, regime)
        regime_adj = regime_eval['adjustment'] / 100.0
        if regime_adj != 0:
            adjustments.append({
                'source': 'regime',
                'value': round(regime_adj, 3),
                'reason': f"Regime {regime_eval['action']} ({regime_eval['win_rate']}% WR, {regime_eval['total_trades']} trades)"
            })
            total_adjustment += regime_adj * self.regime_weight

        # 3. Pattern-level bonus (specific pair+regime+signal match)
        if regime_eval['signals']:
            for s in regime_eval['signals']:
                if s['signal'] == signal and s['trades'] >= 3:
                    pattern_wr = s['win_rate']
                    if pattern_wr >= 70:
                        pattern_adj = 0.08
                        desc = "High-confidence pattern"
                    elif pattern_wr >= 55:
                        pattern_adj = 0.04
                        desc = "Good pattern"
                    elif pattern_wr >= 40:
                        pattern_adj = 0.0
                        desc = "Average pattern"
                    elif pattern_wr >= 25:
                        pattern_adj = -0.05
                        desc = "Weak pattern"
                    else:
                        pattern_adj = -0.10
                        desc = "Failing pattern"
                    
                    adjustments.append({
                        'source': 'pattern',
                        'value': round(pattern_adj, 3),
                        'reason': f"{desc}: {pair}+{regime}+{signal} = {pattern_wr}% WR ({s['trades']} trades)"
                    })
                    total_adjustment += pattern_adj * self.pattern_weight
                    break

        # 4. Calculate adjusted confidence
        adjusted = raw_confidence + total_adjustment
        
        # Cap at reasonable bounds
        adjusted = max(0.25, min(0.95, adjusted))

        # Determine strength
        if adjusted >= 0.65:
            strength = "STRONG"
        elif adjusted >= 0.55:
            strength = "MEDIUM"
        else:
            strength = "WEAK"

        return {
            'pair': pair,
            'regime': regime,
            'signal': signal,
            'raw_confidence': round(raw_confidence, 3),
            'adjusted_confidence': round(adjusted, 3),
            'total_adjustment': round(total_adjustment, 3),
            'strength': strength,
            'adjustments': adjustments,
            'pair_quality': pair_eval['quality'],
            'regime_action': regime_eval['action'],
        }

    def calibrate_signal(self, signal_dict: Dict, regime: str) -> Dict:
        """
        Calibrate a signal dictionary directly.
        
        Args:
            signal_dict: Standard signal dict with 'pair', 'signal', 'confidence'
            regime: Current market regime
            
        Returns:
            Calibrated signal dict (original + adjusted fields)
        """
        pair = signal_dict.get('pair', 'UNKNOWN')
        signal = signal_dict.get('signal', 'UNKNOWN')
        raw_conf = signal_dict.get('confidence', 0.50)

        calibration = self.calibrate(pair, regime, signal, raw_conf)

        # Merge calibration into signal
        calibrated_signal = dict(signal_dict)
        calibrated_signal['raw_confidence'] = calibration['raw_confidence']
        calibrated_signal['adjusted_confidence'] = calibration['adjusted_confidence']
        calibrated_signal['confidence_adjustment'] = calibration['total_adjustment']
        calibrated_signal['confidence_strength'] = calibration['strength']
        calibrated_signal['pair_quality'] = calibration['pair_quality']
        calibrated_signal['regime_action'] = calibration['regime_action']
        calibrated_signal['calibration_reasons'] = [a['reason'] for a in calibration['adjustments']]

        return calibrated_signal

    def summary(self):
        """Print confidence calibrator summary"""
        print("=" * 55)
        print("  CONFIDENCE CALIBRATOR - Volume 9 Module 4")
        print("=" * 55)

        # Test with standard scenarios
        test_cases = [
            ("USDJPY", "RANGING", "BUY", 0.55),
            ("NZDUSD", "RANGING", "SELL", 0.55),
            ("NZDUSD", "BREAKOUT", "BUY", 0.55),
            ("AUDUSD", "BREAKOUT", "SELL", 0.60),
            ("EURUSD", "RANGING", "SELL", 0.53),
        ]

        print("\n  Calibration Examples:")
        print("  " + "-" * 50)

        for pair, regime, signal, raw in test_cases:
            result = self.calibrate(pair, regime, signal, raw)
            arrow = "->"
            print(f"\n  {pair} {regime} {signal}")
            print(f"    Raw: {result['raw_confidence']:.3f} {arrow} Adjusted: {result['adjusted_confidence']:.3f} ({result['strength']})")
            print(f"    Adjustment: {result['total_adjustment']:+.3f}")
            for adj in result['adjustments']:
                print(f"      [{adj['source']}] {adj['value']:+.3f} - {adj['reason']}")

        # Stats
        print("\n  Calibration Stats:")
        conn = __import__('sqlite3').connect(self.memory.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(DISTINCT pair||regime||signal) FROM strategy_memory WHERE trades >= 3")
        patterns = c.fetchone()[0]
        conn.close()
        print(f"    Calibratable patterns: {patterns}")
        print(f"    Pair weight: {self.pair_weight}")
        print(f"    Regime weight: {self.regime_weight}")
        print(f"    Pattern weight: {self.pattern_weight}")

        print("\n  STATUS: CONFIDENCE CALIBRATOR OPERATIONAL")
        print("=" * 55)


if __name__ == "__main__":
    cc = ConfidenceCalibrator()
    cc.summary()
