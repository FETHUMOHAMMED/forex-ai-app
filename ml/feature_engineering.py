"""
ML Feature Engineering - Extract features from MT5 data for training.
"""
import pandas as pd
import numpy as np

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Convert OHLCV data into ML features."""
    df = df.copy()
    
    # Price features
    df['returns_1'] = df['close'].pct_change(1)
    df['returns_5'] = df['close'].pct_change(5)
    df['returns_10'] = df['close'].pct_change(10)
    df['hl_ratio'] = (df['high'] - df['low']) / df['close']
    df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.0001)
    
    # Volume features
    if 'volume' in df.columns:
        df['vol_change_5'] = df['volume'].pct_change(5)
        df['vol_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
    
    # Volatility
    df['atr_14'] = (df['high'] - df['low']).rolling(14).mean()
    df['atr_ratio'] = df['atr_14'] / df['close']
    
    # Moving averages
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_cross'] = (df['sma_20'] - df['sma_50']) / df['close']
    
    # Momentum
    df['rsi_14'] = compute_rsi(df['close'], 14)
    df['momentum_10'] = df['close'] - df['close'].shift(10)
    
    # Drop NaN
    df = df.dropna()
    
    return df

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / (avg_loss + 0.0001)
    return 100 - (100 / (1 + rs))

FEATURE_COLUMNS = [
    'returns_1', 'returns_5', 'returns_10', 'hl_ratio', 'close_position',
    'vol_change_5', 'vol_ratio', 'atr_14', 'atr_ratio',
    'sma_cross', 'rsi_14', 'momentum_10'
]

print(f"Feature engineering ready: {len(FEATURE_COLUMNS)} features")
for f in FEATURE_COLUMNS:
    print(f"  {f}")
