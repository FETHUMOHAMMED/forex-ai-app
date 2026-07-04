"""
apply_best_params.py – Updated to use the latest ML optimization CSV.
"""

import os
import glob
import json
import pandas as pd

def apply_best_params():
    # 1. Find the most recent ml_optimization CSV
    csv_files = glob.glob("ml_optimization_*.csv")
    if not csv_files:
        # Fallback to any optimization_results CSV
        csv_files = glob.glob("optimization_results_*.csv")
    if not csv_files:
        print("❌ No optimization CSV found. Run your tick backtest first.")
        return

    # Sort by modification time, newest first
    csv_files.sort(key=os.path.getmtime, reverse=True)
    csv_path = csv_files[0]
    print(f"📄 Using: {csv_path}")

    # 2. Read the CSV and get the best row (first row is highest score)
    df = pd.read_csv(csv_path)
    best = df.iloc[0]

    # 3. Load current config.json
    config_path = "config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    # 4. Update global parameters that apply to all accounts
    #    (only if the column exists in the CSV)
    param_map = {
        "min_confidence": "min_confidence",
        "risk_percent": "risk_percent",
        "trail_atr_mult": "trail_atr_mult",
        "atr_min_non_jpy": "atr_min_non_jpy",
        "atr_max_non_jpy": "atr_max_non_jpy",
        "atr_min_jpy": "atr_min_jpy",
        "atr_max_jpy": "atr_max_jpy",
    }

    for csv_col, config_key in param_map.items():
        if csv_col in best:
            config[config_key] = float(best[csv_col])
            print(f"   ✅ Updated global {config_key} → {best[csv_col]}")

    # 5. (Optional) Apply the same values to each account's individual settings
    #    If your accounts use the global fallback, they're already covered.
    #    If you want each account to store its own values, uncomment the block below.
    #
    # for acc in config.get("accounts", []):
    #     for csv_col, config_key in param_map.items():
    #         if csv_col in best:
    #             acc[config_key] = float(best[csv_col])

    # 6. Save updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

    print("✅ config.json updated with best parameters.")

if __name__ == "__main__":
    apply_best_params()