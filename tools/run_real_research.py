"""Run research pipeline on real MT5 data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pickle
import pandas as pd
from packages.research.research_pipeline import ResearchPipeline

def main():
    # Load real data
    data_path = Path("data/research/all_historical_data.pkl")
    if not data_path.exists():
        print("No historical data found. Run download_historical_data.py first.")
        return
    
    print("Loading historical data...")
    with open(data_path, 'rb') as f:
        all_data = pickle.load(f)
    
    # Combine data for analysis
    print("Preparing data for research...")
    
    # Start with EURUSD M5 as primary timeframe
    if "EURUSD" in all_data and "M5" in all_data["EURUSD"]:
        m5_data = all_data["EURUSD"]["M5"]
        
        # Run research pipeline
        pipeline = ResearchPipeline()
        strategy = pipeline.run_pipeline(m5_data)
        
        print("\n" + "="*60)
        print("REAL DATA RESEARCH COMPLETE")
        print("="*60)
        print(f"Strategy: {strategy.strategy_id}")
        print(f"Status: {strategy.to_production_format()['status']}")
        print(f"Sample size: {strategy.validation_results.get('sample_size', 0)}")
        print(f"Expectancy: {strategy.validation_results.get('expectancy', 0):.3f}")
        print(f"Profit Factor: {strategy.validation_results.get('profit_factor', 0):.2f}")
        
    else:
        print("EURUSD M5 data not found in the dataset")

if __name__ == "__main__":
    main()
