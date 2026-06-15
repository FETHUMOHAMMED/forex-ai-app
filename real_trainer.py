"""
REAL FOREX AI TRAINER – Alpha Vantage (Reliable, works now)
"""

from alpha_vantage.foreignexchange import ForeignExchange
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score
import joblib
import os
import time
import warnings
warnings.filterwarnings('ignore')

class RealForexTrainer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.pairs = {
            'EURUSD': 'EUR',
            'GBPUSD': 'GBP',
            'USDJPY': 'JPY',
            'AUDUSD': 'AUD',
            'USDCAD': 'CAD'
        }
        self.feature_cols = [
            'rsi', 'macd', 'macd_signal', 'atr', 'volume_ratio',
            'bb_upper', 'bb_lower', 'fvg_buy', 'fvg_sell',
            'ob_buy', 'ob_sell', 'returns', 'high_low_ratio'
        ]

    def fetch_data(self, pair, from_currency, to_currency='USD', outputsize='full'):
        """Fetch daily forex data from Alpha Vantage"""
        print(f"📥 Fetching {pair} from Alpha Vantage...")
        fx = ForeignExchange(key=self.api_key)
        data, _ = fx.get_currency_exchange_daily(
            from_symbol=from_currency,
            to_symbol=to_currency,
            outputsize=outputsize
        )
        # data is a DataFrame with columns: open, high, low, close, volume
        data.columns = ['open', 'high', 'low', 'close', 'volume']
        data = data.iloc[::-1]  # reverse to chronological order
        return data

    def add_features(self, df):
        if df is None or len(df) < 50:
            return None
        
        # Price action
        df['returns'] = df['close'].pct_change()
        df['high_low_ratio'] = (df['high'] - df['low']) / df['close']
        
        # RSI (14)
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
        tr = np.maximum(df['high'] - df['low'],
                        np.maximum(abs(df['high'] - df['close'].shift()),
                                   abs(df['low'] - df['close'].shift())))
        df['atr'] = tr.rolling(14).mean()
        
        # Volume ratio
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # ICT/SMC (simplified)
        df['fvg_buy'] = ((df['high'].shift(2) < df['low']).astype(int))
        df['fvg_sell'] = ((df['low'].shift(2) > df['high']).astype(int))
        df['ob_buy'] = ((df['low'] > df['low'].shift(1)) & (df['low'].shift(1) > df['low'].shift(2))).astype(int)
        df['ob_sell'] = ((df['high'] < df['high'].shift(1)) & (df['high'].shift(1) < df['high'].shift(2))).astype(int)
        
        # Target: next day's direction
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        df = df.dropna()
        return df

    def train_for_pair(self, pair, from_curr, to_curr='USD'):
        print(f"\n{'='*60}")
        print(f"Training {pair}")
        print('='*60)
        
        try:
            df = self.fetch_data(pair, from_curr, to_curr)
            df = self.add_features(df)
            if df is None or len(df) < 500:
                print(f"❌ Insufficient data for {pair}")
                return None
            
            X = df[self.feature_cols].fillna(0)
            y = df['target']
            
            buy_ratio = y.mean()
            print(f"Class distribution: BUY = {buy_ratio:.1%}, SELL = {1-buy_ratio:.1%}")
            neg = len(y) - y.sum()
            pos = y.sum()
            scale = neg / pos if pos > 0 else 1
            print(f"Scale_pos_weight: {scale:.3f}")
            
            # Walk-forward validation
            tscv = TimeSeriesSplit(n_splits=3)
            scores = []
            for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                model = xgb.XGBClassifier(
                    n_estimators=100, max_depth=5, learning_rate=0.05,
                    subsample=0.8, colsample_bytree=0.8, scale_pos_weight=scale,
                    random_state=42, use_label_encoder=False, eval_metric='logloss',
                    early_stopping_rounds=10
                )
                model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
                pred = model.predict(X_val)
                acc = accuracy_score(y_val, pred)
                scores.append(acc)
                print(f"  Fold {fold}: Accuracy = {acc:.2%}")
            
            avg_acc = np.mean(scores)
            print(f"\n✅ Walk-forward accuracy: {avg_acc:.2%} (+/- {np.std(scores):.2%})")
            
            # Retrain on all data
            final_model = xgb.XGBClassifier(
                n_estimators=100, max_depth=5, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8, scale_pos_weight=scale,
                random_state=42, use_label_encoder=False, eval_metric='logloss'
            )
            final_model.fit(X, y)
            
            os.makedirs('models', exist_ok=True)
            filename = f"models/{pair}_xgboost.joblib"
            joblib.dump(final_model, filename)
            print(f"💾 Model saved: {filename}")
            
            return final_model, avg_acc
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def run(self):
        print("="*60)
        print("REAL FOREX AI TRAINER – Alpha Vantage")
        print("="*60)
        results = {}
        for pair, from_curr in self.pairs.items():
            result = self.train_for_pair(pair, from_curr)
            if result:
                model, acc = result
                results[pair] = acc
            time.sleep(15)  # Respect free tier rate limit (5 calls/min)
        print("\n" + "="*60)
        print("TRAINING COMPLETE – Summary")
        print("="*60)
        for pair, acc in results.items():
            print(f"{pair}: {acc:.2%}")

if __name__ == "__main__":
    # Get your free API key from https://www.alphavantage.co/support/#api-key
    API_KEY = "2XBRAAK6D0S8D0LE"
    trainer = RealForexTrainer(API_KEY)
    trainer.run()