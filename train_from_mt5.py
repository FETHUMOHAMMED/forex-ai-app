"""
Train XGBoost models using REAL MT5 historical data (15-min bars).
Includes enhanced ICT patterns for better feature engineering.
"""

import os
import sys
import warnings
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import xgboost as xgb
import joblib

# MT5 import
try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 not installed. Run: pip install MetaTrader5")
    sys.exit(1)

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class MT5DataTrainer:
    def __init__(self):
        self.pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
                      'USDCHF', 'NZDUSD', 'USDSGD']
        self.timeframe = mt5.TIMEFRAME_M15
        self.lookback_months = 24          # 2 years
        self.bars_to_fetch = 20000         # Enough for 15-min data

        # Connect to MT5
        if not mt5.initialize():
            logger.error("MT5 init failed")
            sys.exit(1)
        logger.info("✅ MT5 connected")

    def fetch_mt5_data(self, pair):
        """Get historical rates from MT5"""
        # Find actual symbol name (Exness may add suffixes)
        candidates = [pair, f"{pair}m", f"{pair}.", f"{pair}micro", f"{pair}pro"]
        symbol = None
        for sym in candidates:
            if mt5.symbol_select(sym, True):
                symbol = sym
                break
        if not symbol:
            logger.warning(f"Symbol not found for {pair}")
            return None

        # Fetch rates
        rates = mt5.copy_rates_from_pos(symbol, self.timeframe, 0, self.bars_to_fetch)
        if rates is None or len(rates) == 0:
            logger.warning(f"No data for {pair}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.columns = ['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
        df['volume'] = df['tick_volume']
        df = df[['open', 'high', 'low', 'close', 'volume']]
        logger.info(f"Fetched {len(df)} bars for {pair}")
        return df

    def add_features(self, df):
        """Add all technical indicators including enhanced ICT patterns"""
        if df is None or len(df) < 200:
            return None
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
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # Bollinger Bands
        df['bb_mid'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()

        # Volume ratio
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

        # Original ICT patterns
        df['fvg_buy'] = (df['high'].shift(2) < df['low']).astype(int)
        df['fvg_sell'] = (df['low'].shift(2) > df['high']).astype(int)
        df['ob_buy'] = ((df['low'] > df['low'].shift(1)) &
                        (df['low'].shift(1) > df['low'].shift(2))).astype(int)
        df['ob_sell'] = ((df['high'] < df['high'].shift(1)) &
                         (df['high'].shift(1) < df['high'].shift(2))).astype(int)

        # ========== ENHANCED ICT PATTERNS ==========
        # Breaker Block (BB)
        df['bb_buy'] = ((df['low'].shift(1) < df['low'].shift(2)) &
                        (df['high'] > df['high'].shift(1)) &
                        (df['close'] > df['high'].shift(1))).astype(int)
        df['bb_sell'] = ((df['high'].shift(1) > df['high'].shift(2)) &
                         (df['low'] < df['low'].shift(1)) &
                         (df['close'] < df['low'].shift(1))).astype(int)

        # Liquidity Void (LV)
        df['lv_buy'] = (df['low'] > df['high'].shift(1)).astype(int)
        df['lv_sell'] = (df['high'] < df['low'].shift(1)).astype(int)

        # Market Structure Shift (MSS)
        swing_high = df['high'].rolling(5).max().shift(1)
        swing_low = df['low'].rolling(5).min().shift(1)
        df['mss_buy'] = ((df['close'] > swing_high) & (df['close'].shift(1) <= swing_high)).astype(int)
        df['mss_sell'] = ((df['close'] < swing_low) & (df['close'].shift(1) >= swing_low)).astype(int)

        # Target: future price direction (next bar)
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)

        df = df.dropna()
        return df

    def train_pair(self, pair):
        logger.info(f"\n{'='*50}\nTraining {pair}\n{'='*50}")
        df = self.fetch_mt5_data(pair)
        if df is None:
            return None
        df = self.add_features(df)
        if df is None or len(df) < 500:
            logger.warning(f"Insufficient data for {pair} after indicators")
            return None

        feature_cols = [
            'rsi', 'macd', 'macd_signal', 'atr', 'volume_ratio',
            'bb_upper', 'bb_lower', 'fvg_buy', 'fvg_sell',
            'ob_buy', 'ob_sell', 'returns', 'high_low_ratio',
            'bb_buy', 'bb_sell', 'lv_buy', 'lv_sell', 'mss_buy', 'mss_sell'
        ]
        X = df[feature_cols].fillna(0)
        y = df['target']

        # Time-based split: train on first 80%, test on last 20%
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        # Handle class imbalance
        pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1]) if y_train.sum() > 0 else 1

        model = xgb.XGBClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=pos_weight,
            random_state=42,
            eval_metric='logloss'
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

        train_acc = model.score(X_train, y_train)
        test_acc = model.score(X_test, y_test)
        logger.info(f"Train Accuracy: {train_acc:.2%}")
        logger.info(f"Test Accuracy:  {test_acc:.2%}")

        # Save model
        os.makedirs('models', exist_ok=True)
        model_path = f"models/{pair}_xgboost.joblib"
        joblib.dump(model, model_path)
        logger.info(f"💾 Model saved to {model_path}")

        return model, test_acc

    def run(self):
        logger.info("Starting real-data training from MT5 with enhanced ICT features...")
        results = {}
        for pair in self.pairs:
            result = self.train_pair(pair)
            if result:
                _, acc = result
                results[pair] = acc
        mt5.shutdown()
        logger.info("\n" + "="*50)
        logger.info("TRAINING COMPLETE")
        for pair, acc in results.items():
            logger.info(f"{pair}: {acc:.2%} accuracy")
        logger.info("✅ New models saved. Restart the AI service to use them.")

if __name__ == "__main__":
    trainer = MT5DataTrainer()
    trainer.run()