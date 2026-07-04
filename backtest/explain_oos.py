"""
SHAP EXPLAINABILITY FOR ALL PAIRS
Generates summary bar, beeswarm, and dependence plots for each pair's model.
Uses the most recent 6 months of H1 data, filtered per pair.
"""

import shap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
import MetaTrader5 as mt5
from datetime import datetime
from risk.features import FEATURE_COLUMNS
import os

# ------- Config -------
PAIRS = ['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NZDUSD','USDSGD']
FEATURE_COLS = FEATURE_COLUMNS
OUTPUT_DIR = 'shap_plots'

# ------- Load data with pair column -------
def load_oos_data():
    """Fetches H1 data for all pairs, adds features, and returns a combined DataFrame
    with a 'pair' column."""
    from real_ai_service import RealAITrader
    ai = RealAITrader()
    frames = []
    for pair in PAIRS:
        symbol = None
        for suffix in ['', 'm', '.', 'pro']:
            if mt5.symbol_select(pair + suffix, True):
                symbol = pair + suffix
                break
        if not symbol:
            continue
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1,
                                     pd.to_datetime('2023-01-01'),
                                     datetime.now())
        if rates is None or len(rates) < 500:
            continue
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        df = df[['open','high','low','close','volume']]
        df = ai.add_indicators(df)
        if df is None or len(df) < 200:
            continue

        # Extra features
        h4 = df['close'].resample('4h').last()
        h4_ema200 = h4.ewm(span=200).mean()
        df['h4_ema200'] = h4_ema200.reindex(df.index, method='ffill')
        df['dist_from_h4_ema'] = (df['close'] - df['h4_ema200']) / df['h4_ema200'] * 100
        hours = df.index.hour
        df['london'] = ((hours >= 7) & (hours < 12)).astype(int)
        df['newyork'] = ((hours >= 13) & (hours < 18)).astype(int)
        atr_long = df['atr'].rolling(200).median()
        df['vol_high'] = (df['atr'] > atr_long * 1.5).astype(int)

        model = ai.models.get(pair)
        if model is None:
            continue
        X = df[FEATURE_COLS].fillna(0).values
        preds = model.predict(X)
        proba = model.predict_proba(X)
        df['ml_signal'] = preds
        df['ml_conf'] = np.where(preds == 1, proba[:, 1], proba[:, 0])

        # Last 6 months
        latest_date = df.index.max()
        cutoff = latest_date - pd.DateOffset(months=6)
        df = df[df.index >= cutoff]
        if len(df) < 100:
            continue

        df['pair'] = pair
        frames.append(df)
        print(f"   ✅ {pair}: {len(df)} OOS bars ({df.index.min().date()} → {df.index.max().date()})")

    if not frames:
        return None
    full = pd.concat(frames)
    return full.dropna()

# ------- SHAP for a single pair -------
def shap_for_pair(pair, model_path, X_pair):
    """Generate and save SHAP plots for one pair."""
    try:
        model = joblib.load(model_path)
    except Exception as e:
        print(f"   ❌ Could not load model for {pair}: {e}")
        return

    # Extract base estimator from calibrated wrapper
    if hasattr(model, 'estimator_'):
        base_model = model.estimator_
    elif hasattr(model, 'calibrated_classifiers_'):
        base_model = model.calibrated_classifiers_[0].estimator
    else:
        base_model = model

    # Sample up to 5000 rows for speed
    n_sample = min(5000, len(X_pair))
    X_sample = X_pair.sample(n_sample, random_state=42)

    explainer = shap.TreeExplainer(base_model)
    shap_values = explainer.shap_values(X_sample)
    if isinstance(shap_values, list):
        shap_vals = shap_values[1]   # class 1 (BUY)
    else:
        shap_vals = shap_values

    # ----- Plot 1: Summary bar -----
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_vals, X_sample, plot_type="bar", show=False)
    plt.title(f"{pair} – SHAP Feature Importance", fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"{pair}_shap_bar.png"), dpi=150)
    plt.close()

    # ----- Plot 2: Beeswarm -----
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_vals, X_sample, show=False)
    plt.title(f"{pair} – SHAP Beeswarm", fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"{pair}_shap_beeswarm.png"), dpi=150)
    plt.close()

    # ----- Plot 3: Dependence for top feature -----
    top_feature = X_sample.columns[np.argmax(np.abs(shap_vals).mean(0))]
    plt.figure(figsize=(10, 6))
    shap.dependence_plot(top_feature, shap_vals, X_sample, show=False)
    plt.title(f"{pair} – SHAP Dependence: {top_feature}", fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"{pair}_shap_dependence_{top_feature}.png"), dpi=150)
    plt.close()

    print(f"   ✅ SHAP plots saved for {pair} (top feature: {top_feature})")

# ------- Main -------
if __name__ == "__main__":
    print("📥 Loading recent OOS data for multi‑pair SHAP analysis...")
    if not mt5.initialize():
        print("❌ MT5 not running.")
        exit()

    df = load_oos_data()
    if df is None or len(df) < 100:
        print("❌ Not enough data.")
        exit()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for pair in PAIRS:
        X_pair = df[df['pair'] == pair][FEATURE_COLS].fillna(0)
        if len(X_pair) < 100:
            print(f"   ⚠️  {pair}: insufficient OOS bars, skipping")
            continue
        model_path = f"models/{pair}_xgboost.joblib"
        shap_for_pair(pair, model_path, X_pair)

    print("\n✅ Multi‑pair SHAP analysis complete. Plots saved in 'shap_plots/' folder.")