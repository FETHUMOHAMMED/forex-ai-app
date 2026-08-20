"""V3_REGIME - Precise, Testable Strategy Definition."""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timezone

@dataclass
class StrategyParameters:
    """Every parameter must be numeric and testable."""
    
    # HTF Bias (H4)
    htf_ema_period: int = 200
    htf_bias_lookback: int = 100
    
    # Liquidity Sweep (M15)
    liquidity_lookback_bars: int = 50
    sweep_wick_ratio: float = 0.5  # Wick must be 50% of range
    
    # Structure Shift (M5)
    mss_lookback_bars: int = 20
    mss_break_distance_pips: float = 2.0  # Must break by 2 pips
    
    # FVG/OB Detection (M5)
    fvg_min_size_pips: float = 3.0
    fvg_max_age_bars: int = 15
    ob_lookback_bars: int = 30
    
    # Entry Conditions
    max_spread_pips: float = 1.5
    session_start_hour: int = 7
    session_end_hour: int = 11
    max_news_proximity_minutes: int = 30
    
    # Risk Management
    sl_buffer_pips: float = 1.5
    tp_rr_multiple: float = 2.0
    max_risk_pct: float = 0.0005  # 0.05%
    
    # Execution
    max_slippage_pips: float = 0.5
    max_execution_delay_seconds: int = 5

class StrategyHypothesis:
    """Formal, testable hypothesis for V3_REGIME."""
    
    def __init__(self, params: StrategyParameters = None):
        self.params = params or StrategyParameters()
        self.hypothesis_id = "V3_REGIME_2026_08"
        
    def define_hypothesis(self) -> dict:
        """Return the formal hypothesis statement."""
        return {
            "hypothesis_id": self.hypothesis_id,
            "statement": (
                "When H4 shows directional bias (EMA200 + price position), "
                "AND M15 shows liquidity sweep (wick through recent extreme), "
                "AND M5 confirms structure shift (break of minor swing), "
                "AND M5 shows FVG/OB in direction of shift, "
                "THEN entering with 1:2 R:R produces positive expectancy "
                "after costs across multiple currency pairs."
            ),
            "independent_variables": [
                "htf_bias_direction",
                "liquidity_sweep_quality",
                "mss_confirmation",
                "fvg_quality",
                "session_filter",
                "spread_filter"
            ],
            "dependent_variable": "trade_outcome_r_multiple",
            "control_variables": [
                "currency_pair",
                "time_of_day",
                "market_regime"
            ],
            "success_criteria": {
                "min_expectancy_r": 0.2,  # Minimum 0.2R per trade
                "min_profit_factor": 1.3,
                "max_drawdown_pct": 10,
                "min_sample_size": 100,
                "min_win_rate": 0.35  # Allow lower win rate with good R:R
            },
            "invalidation_criteria": [
                "expectancy < 0 after 50 trades",
                "profit_factor < 1.0 after 100 trades",
                "drawdown > 15%",
                "performance degrades in high volatility regime"
            ]
        }
    
    def validate_signal(self, signal: dict) -> tuple[bool, List[str]]:
        """Check if a signal meets ALL precise criteria."""
        failures = []
        checks = []
        
        # Check HTF Bias
        if "htf_bias" not in signal:
            failures.append("MISSING_HTF_BIAS")
        elif signal["htf_bias"] not in ["BULLISH", "BEARISH"]:
            failures.append("INVALID_HTF_BIAS")
        
        # Check Liquidity Sweep
        if "liquidity_sweep" not in signal:
            failures.append("MISSING_LIQUIDITY_SWEEP")
        elif signal["liquidity_sweep"]["wick_ratio"] < self.params.sweep_wick_ratio:
            failures.append(f"WEAK_SWEEP: {signal['liquidity_sweep']['wick_ratio']:.2f} < {self.params.sweep_wick_ratio}")
        
        # Check MSS
        if "mss" not in signal:
            failures.append("MISSING_MSS")
        elif signal["mss"]["break_pips"] < self.params.mss_break_distance_pips:
            failures.append(f"WEAK_MSS: {signal['mss']['break_pips']:.2f} < {self.params.mss_break_distance_pips}")
        
        # Check FVG
        if "fvg" not in signal:
            failures.append("MISSING_FVG")
        elif signal["fvg"]["size_pips"] < self.params.fvg_min_size_pips:
            failures.append(f"SMALL_FVG: {signal['fvg']['size_pips']:.2f} < {self.params.fvg_min_size_pips}")
        
        # Check Spread
        if "spread_pips" in signal and signal["spread_pips"] > self.params.max_spread_pips:
            failures.append(f"HIGH_SPREAD: {signal['spread_pips']:.2f} > {self.params.max_spread_pips}")
        
        # Check Session
        current_hour = datetime.now(timezone.utc).hour
        if current_hour < self.params.session_start_hour or current_hour > self.params.session_end_hour:
            failures.append(f"OUTSIDE_SESSION: {current_hour}:00 UTC")
        
        return len(failures) == 0, failures
    
    def calculate_expected_r(self, entry: float, sl: float, tp: float, direction: str) -> float:
        """Calculate the R:R ratio for a trade."""
        if direction == "BUY":
            risk = entry - sl
            reward = tp - entry
        else:  # SELL
            risk = sl - entry
            reward = entry - tp
        
        if risk <= 0:
            return 0.0
        
        return reward / risk

if __name__ == "__main__":
    # Test the hypothesis definition
    hyp = StrategyHypothesis()
    print(json.dumps(hyp.define_hypothesis(), indent=2))
    
    # Test signal validation
    test_signal = {
        "htf_bias": "BULLISH",
        "liquidity_sweep": {"wick_ratio": 0.6},
        "mss": {"break_pips": 2.5},
        "fvg": {"size_pips": 4.0},
        "spread_pips": 1.2,
    }
    
    valid, failures = hyp.validate_signal(test_signal)
    print(f"\nSignal Valid: {valid}")
    if failures:
        print(f"Failures: {failures}")
