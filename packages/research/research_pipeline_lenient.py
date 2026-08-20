"""Research pipeline with lenient strategy parameters."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.research.research_pipeline import ResearchPipeline, ResearchConfig

class LenientResearchPipeline(ResearchPipeline):
    """Research pipeline with more lenient strategy parameters."""
    
    def _define_strategy(self) -> dict:
        """Define lenient strategy parameters."""
        return {
            "h4_ema_fast": 20,      # Faster EMA
            "h4_ema_slow": 100,     # Slower EMA
            "sweep_lookback": 100,  # Longer lookback
            "sweep_wick_ratio": 0.3, # More lenient wick ratio
            "mss_break_pips": 1.0,  # Easier MSS
            "fvg_min_size_pips": 1.5, # Smaller FVG
            "sl_buffer_pips": 1.0,  # Tighter SL
            "tp_rr_ratio": 1.5,     # Lower target
            "max_spread_pips": 2.5, # More lenient spread
            "session_start": 6,     # Earlier session
            "session_end": 14       # Later session
        }

if __name__ == "__main__":
    import pandas as pd
    import pickle
    
    # Load data
    with open("data/research/all_historical_data.pkl", "rb") as f:
        all_data = pickle.load(f)
    
    data = all_data["EURUSD"]["M5"]
    
    # Run lenient pipeline
    pipeline = LenientResearchPipeline()
    strategy = pipeline.run_pipeline(data)
    
    print("\n" + "="*60)
    print("LENIENT RESEARCH COMPLETE")
    print("="*60)
    print(f"Strategy: {strategy.strategy_id}")
    print(f"Status: {strategy.to_production_format()['status']}")
    if strategy.validation_results:
        print(f"Sample size: {strategy.validation_results.get('sample_size', 0)}")
        print(f"Expectancy: {strategy.validation_results.get('expectancy', 0):.3f}")
        print(f"Win rate: {strategy.validation_results.get('win_rate', 0):.2%}")
