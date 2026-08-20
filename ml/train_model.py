"""
Train ML models from historical MT5 data.
Run this ONCE to generate model files.
"""
import sys, os, pickle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from ml.feature_engineering import engineer_features, FEATURE_COLUMNS

def build_training_data(pair: str, days: int = 180) -> pd.DataFrame:
    """Build labeled training dataset from historical data."""
    symbol = pair + 'm'
    mt5.symbol_select(symbol, True)
    
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start, end)
    
    if rates is None or len(rates) < 100:
        print(f"  {pair}: Not enough data")
        return None
    
    df = pd.DataFrame(rates)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    
    # Engineer features
    df = engineer_features(df)
    
    # Label: 1 if price goes up in next 5 candles, 0 if down
    df['future_return'] = df['close'].shift(-5) / df['close'] - 1
    df['label'] = (df['future_return'] > 0.001).astype(int)  # 1 = BUY (up > 0.1%)
    
    # Drop rows without labels
    df = df.dropna()
    
    print(f"  {pair}: {len(df)} samples, {df['label'].sum()} buy / {len(df)-df['label'].sum()} sell")
    return df

def train_model(pair: str, df: pd.DataFrame):
    """Train XGBoost model and save to disk."""
    try:
        from xgboost import XGBClassifier
    except ImportError:
        print("  Installing xgboost...")
        import subprocess
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'xgboost', '--quiet'])
        from xgboost import XGBClassifier
    
    X = df[FEATURE_COLUMNS].values
    y = df['label'].values
    
    # Train/test split
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"  {pair}: Train acc={train_acc:.3f}, Test acc={test_acc:.3f}")
    
    # Save
    model_path = os.path.join(os.path.dirname(__file__), 'models', f'{pair}.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"  {pair}: Saved to {model_path}")
    
    return model

if __name__ == '__main__':
    mt5.initialize()
    
    pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'NZDUSD', 'AUDUSD']
    
    for pair in pairs:
        print(f"\n{pair}:")
        df = build_training_data(pair, days=180)
        if df is not None and len(df) > 50:
            train_model(pair, df)
    
    mt5.shutdown()
    print("\nDone! Models saved to ml/models/")
