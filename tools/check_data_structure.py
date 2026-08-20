"""Check the structure of saved data."""
import pickle
from pathlib import Path

def check_data():
    """Check pickle file structure."""
    data_path = Path("data/research/all_historical_data.pkl")
    
    if not data_path.exists():
        print("Data file not found!")
        return
    
    print("Loading data...")
    with open(data_path, "rb") as f:
        all_data = pickle.load(f)
    
    print(f"\nTop-level keys: {list(all_data.keys())}")
    
    if "EURUSD" in all_data:
        print(f"\nEURUSD keys: {list(all_data['EURUSD'].keys())}")
        
        # Check each timeframe
        for tf in all_data["EURUSD"]:
            df = all_data["EURUSD"][tf]
            print(f"\n{tf}:")
            print(f"  Type: {type(df)}")
            print(f"  Shape: {df.shape if hasattr(df, 'shape') else 'N/A'}")
            print(f"  Columns: {list(df.columns) if hasattr(df, 'columns') else 'N/A'}")
    else:
        print("\nAvailable keys at top level:")
        for key in all_data.keys():
            print(f"  {key}")
            if isinstance(all_data[key], dict):
                for subkey in all_data[key].keys():
                    print(f"    {subkey}")

if __name__ == "__main__":
    check_data()
