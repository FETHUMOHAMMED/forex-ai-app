"""
Synthetic Forex Data Trainer – Generates realistic price patterns
Trains XGBoost and produces mixed BUY/SELL signals.
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os

def generate_synthetic_forex(n=5000):
    """Generate realistic forex OHLC data with trend and volatility"""
    np.random.seed(42)
    # Random walk with drift
    returns = np.random.normal(0.0001, 0.001, n)  # mean 0.01% per step
    price = 1.1000 + np.cumsum(returns)
    # Add some autocorrelation
    for i in range(1, len(returns)):
        returns[i] += 0.1 * returns[i-1]
    price = 1.1000 + np.cumsum(returns)
    
    # Generate high/low based on typical spreads
    high = price + np.abs(np.random.normal(0, 0.0005, n))
    low = price - np.abs(np.random.normal(0, 0.0005, n))
    open_price = price + np.random.normal(0, 0.0002, n)
    volume = np.random.randint(1000, 10000, n)
    
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': price,
        'volume': volume
    })
    return df

def add_features(df):
    df = df.copy()
    df['returns'] = df['close'].pct_change()
    df['high_low_ratio'] = (df['high'] - df['low']) / df['close']
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp12 = df['close'].ewm(span=12).mean()
    exp26 = df['close'].ewm(span=26).mean()
    df['macd'] = exp12 - exp26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    
    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2*df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2*df['bb_std']
    
    # ATR
    tr = np.maximum(df['high'] - df['low'],
                    np.maximum(abs(df['high'] - df['close'].shift()),
                               abs(df['low'] - df['close'].shift())))
    df['atr'] = tr.rolling(14).mean()
    
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
    
    # ICT/SMC synthetic signals
    df['fvg_buy'] = ((df['high'].shift(2) < df['low']).astype(int))
    df['fvg_sell'] = ((df['low'].shift(2) > df['high']).astype(int))
    df['ob_buy'] = ((df['low'] > df['low'].shift(1)) & (df['low'].shift(1) > df['low'].shift(2))).astype(int)
    df['ob_sell'] = ((df['high'] < df['high'].shift(1)) & (df['high'].shift(1) < df['high'].shift(2))).astype(int)
    
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df = df.dropna()
    return df

def train_and_save(pair_name):
    print(f"Generating synthetic data for {pair_name}...")
    df = generate_synthetic_forex(6000)
    df = add_features(df)
    
    feature_cols = [c for c in ['rsi','macd','macd_signal','atr','volume_ratio',
                                 'bb_upper','bb_lower','fvg_buy','fvg_sell',
                                 'ob_buy','ob_sell','returns','high_low_ratio'] if c in df.columns]
    X = df[feature_cols].fillna(0)
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    model = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.05,
                              subsample=0.8, colsample_bytree=0.8,
                              random_state=42, use_label_encoder=False, eval_metric='logloss')
    model.fit(X_train, y_train)
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"Test accuracy: {acc:.2%}")
    
    os.makedirs('models', exist_ok=True)
    joblib.dump(model, f"models/{pair_name}_xgboost.joblib")
    print(f"Saved model for {pair_name}")

if __name__ == "__main__":
    pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD']
    for p in pairs:
        train_and_save(p)
    print("\n✅ All models saved. You can now run real_ai_service.py")