"""
TRAIN REGIME PREDICTOR
Predicts the next hour's regime (trending / ranging / volatile) for each pair.
Uses ATR acceleration, volume ratio, H4 distance, and current regime.
Saves a RandomForest model per pair.
"""

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
from evolve_regime_params import build_regime_maps, PAIRS, SPREAD_JPY, SPREAD_NON_JPY

# ------- Config -------
FORECAST_HORIZON = 1          # predict next 1 hour's regime
WARMUP_BARS = 200             # minimum bars needed to compute rolling features

# ------- Feature builders -------
def make_features(df):
    """
    Add rolling features to a DataFrame that already has:
    'open','high','low','close','volume','atr','returns', etc.
    The DataFrame must also have a 'regime' column (already mapped).
    """
    df = df.copy()
    
    # ATR acceleration (change in ATR)
    df['atr_accel'] = df['atr'].diff()
    
    # Volume ratio (if not already present)
    if 'volume_ratio' not in df.columns:
        vol_mean = df['volume'].rolling(20).mean()
        df['volume_ratio'] = (df['volume'] / vol_mean).fillna(1)
    
    # Distance from H4 EMA (already computed in GA data, but we recompute here for safety)
    h4 = df['close'].resample('4h').last()
    h4_ema200 = h4.ewm(span=200).mean()
    df['h4_ema200'] = h4_ema200.reindex(df.index, method='ffill')
    df['dist_h4'] = (df['close'] - df['h4_ema200']) / df['h4_ema200'] * 100
    
    # Hour of day
    df['hour'] = df.index.hour
    
    # One‑hot encode current regime (the one that is known at time t)
    regime_dummies = pd.get_dummies(df['regime'], prefix='curr')
    for col in ['curr_trending', 'curr_ranging', 'curr_volatile']:
        if col not in regime_dummies.columns:
            regime_dummies[col] = 0
    df = pd.concat([df, regime_dummies[['curr_trending','curr_ranging','curr_volatile']]], axis=1)
    
    # Target: next hour's regime
    df['target'] = df['regime'].shift(-FORECAST_HORIZON)
    
    # Drop rows where target or features are NaN
    df = df.dropna(subset=['target', 'atr_accel', 'volume_ratio', 'dist_h4', 'hour'])
    return df

# ------- Main -------
if __name__ == '__main__':
    print("📥 Fetching H1 data for regime prediction training...")
    if not mt5.initialize():
        raise RuntimeError("MT5 not running")

    all_data = []
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

        # Add basic indicators (ATR, returns, etc.) – use RealAITrader's method or replicate
        from real_ai_service import RealAITrader
        ai = RealAITrader()
        df = ai.add_indicators(df)
        if df is None or len(df) < 500:
            continue

        # Regime map
        regime_maps = build_regime_maps()   # same as GA
        if pair not in regime_maps:
            continue
        hour_index = df.index.floor('h')
        df['regime'] = hour_index.map(regime_maps[pair]).fillna('volatile')

        df = make_features(df)
        all_data.append(df)
        print(f"✅ {pair}: {len(df)} training rows")

    if not all_data:
        print("❌ No training data")
        exit()

    # Concatenate all pairs (optional: keep per‑pair models for more precision)
    full_df = pd.concat(all_data).dropna()

    # Features and target
    feature_cols = [
        'atr_accel', 'volume_ratio', 'dist_h4', 'hour',
        'curr_trending', 'curr_ranging', 'curr_volatile'
    ]
    X = full_df[feature_cols].values
    y = full_df['target'].values

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train a simple Random Forest
    model = RandomForestClassifier(
        n_estimators=50,
        max_depth=8,
        random_state=42,
        class_weight='balanced'
    )
    model.fit(X_scaled, y)

    # Save model and scaler
    joblib.dump(model, 'regime_predictor.joblib')
    joblib.dump(scaler, 'regime_predictor_scaler.joblib')
    print("\n✅ Regime predictor saved (regime_predictor.joblib, scaler)")
    print("Feature importances:")
    for feat, imp in zip(feature_cols, model.feature_importances_):
        print(f"   {feat}: {imp:.3f}")