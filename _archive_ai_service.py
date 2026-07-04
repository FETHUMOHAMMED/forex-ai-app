"""
FOREX AI TRADING SERVICE - WINDOWS VERSION
ICT + SMC + Simple ML
"""

import pandas as pd
import numpy as np
import yfinance as yf
import xgboost as xgb
from datetime import datetime
import json
import sys
import warnings
import os

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

warnings.filterwarnings('ignore')

class ForexAITrader:
    def __init__(self):
        self.model = None
        self.pairs = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
        self.timeframe = '15m'
        
    def fetch_data(self, pair, days=30):
        """Get forex data"""
        try:
            print(f"[DATA] Fetching {pair}...", flush=True)
            df = yf.download(
                pair, 
                period=f'{days}d', 
                interval=self.timeframe, 
                progress=False,
                auto_adjust=False
            )
            if df.empty:
                return None
            df.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            return df
        except Exception as e:
            print(f"[ERROR] {pair}: {e}", flush=True)
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_atr(self, df, period=14):
        """Calculate ATR"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    def add_indicators(self, df):
        """Add all trading indicators"""
        if df is None or len(df) < 50:
            return df
            
        # RSI
        df['rsi'] = self.calculate_rsi(df['close'], 14)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        
        # ATR
        df['atr'] = self.calculate_atr(df, 14)
        
        # Volume
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # ICT/SMC Indicators
        df['fvg_buy'] = (df['high'].shift(2) < df['low']).astype(int)
        df['fvg_sell'] = (df['low'].shift(2) > df['high']).astype(int)
        df['ob_buy'] = ((df['low'] > df['low'].shift(1)) & (df['low'].shift(1) > df['low'].shift(2))).astype(int)
        df['ob_sell'] = ((df['high'] < df['high'].shift(1)) & (df['high'].shift(1) < df['high'].shift(2))).astype(int)
        
        # Target variable
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        # Replace inf values
        df = df.replace([np.inf, -np.inf], np.nan)
        
        return df.dropna()
    
    def train_model(self, pair='EURUSD=X', days=60):
        """Train XGBoost model"""
        print(f"[TRAIN] Training on {pair}...", flush=True)
        
        df = self.fetch_data(pair, days)
        if df is None:
            return False
            
        df = self.add_indicators(df)
        if df is None or len(df) < 50:
            print(f"[TRAIN] Not enough data for {pair}", flush=True)
            return False
        
        features = ['rsi', 'macd', 'macd_signal', 'atr', 'volume_ratio', 
                   'bb_upper', 'bb_lower', 'fvg_buy', 'fvg_sell', 'ob_buy', 'ob_sell']
        
        existing_features = [f for f in features if f in df.columns]
        
        X = df[existing_features].fillna(0)
        y = df['target']
        
        if len(X) < 50:
            return False
        
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        
        self.model.fit(X, y)
        accuracy = self.model.score(X, y)
        print(f"[TRAIN] Accuracy: {accuracy:.2%}", flush=True)
        return True
    
    def get_signal(self, pair):
        """Get trading signal for a pair"""
        try:
            df = self.fetch_data(pair, days=5)
            if df is None or len(df) < 30:
                return None
            
            df = self.add_indicators(df)
            if df is None or len(df) < 10:
                return None
            
            # ICT Signal
            last = df.iloc[-1]
            ict_buy = last.get('fvg_buy', 0) == 1 or last.get('ob_buy', 0) == 1
            ict_sell = last.get('fvg_sell', 0) == 1 or last.get('ob_sell', 0) == 1
            
            # ML Signal
            features = ['rsi', 'macd', 'macd_signal', 'atr', 'volume_ratio', 
                       'bb_upper', 'bb_lower', 'fvg_buy', 'fvg_sell', 'ob_buy', 'ob_sell']
            existing_features = [f for f in features if f in df.columns]
            
            X = df[existing_features].fillna(0).iloc[-1:]
            
            ml_buy = False
            ml_sell = False
            ml_conf = 0
            
            if self.model and len(X.columns) > 0:
                try:
                    proba = self.model.predict_proba(X)[0]
                    ml_conf = max(proba)
                    ml_pred = self.model.predict(X)[0]
                    ml_buy = ml_pred == 1
                    ml_sell = ml_pred == 0
                except:
                    pass
            
            # Ensemble Decision
            current_price = df['close'].iloc[-1]
            atr = df['atr'].iloc[-1] if 'atr' in df.columns else 0.001
            
            if atr <= 0:
                atr = 0.001
            
            if ict_buy and ml_buy:
                signal = 'BUY'
                strength = 'STRONG'
                confidence = 0.85
                sl = current_price - (atr * 1.5)
                tp = current_price + (atr * 2.5)
            elif ict_sell and ml_sell:
                signal = 'SELL'
                strength = 'STRONG'
                confidence = 0.85
                sl = current_price + (atr * 1.5)
                tp = current_price - (atr * 2.5)
            elif ict_buy and ml_conf > 0.65:
                signal = 'BUY'
                strength = 'MEDIUM'
                confidence = ml_conf
                sl = current_price - (atr * 1.5)
                tp = current_price + (atr * 2.5)
            elif ict_sell and ml_conf > 0.65:
                signal = 'SELL'
                strength = 'MEDIUM'
                confidence = ml_conf
                sl = current_price + (atr * 1.5)
                tp = current_price - (atr * 2.5)
            elif ml_conf > 0.75:
                signal = 'BUY' if ml_buy else 'SELL'
                strength = 'WEAK'
                confidence = ml_conf * 0.9
                sl = current_price - (atr * 1.2) if ml_buy else current_price + (atr * 1.2)
                tp = current_price + (atr * 2.0) if ml_buy else current_price - (atr * 2.0)
            else:
                return None
            
            rr = abs(tp - current_price) / abs(sl - current_price) if abs(sl - current_price) > 0 else 1.5
            
            return {
                'pair': pair.replace('=X', ''),
                'signal': signal,
                'confidence': round(confidence, 3),
                'strength': strength,
                'entry': round(float(current_price), 5),
                'stop_loss': round(float(sl), 5),
                'take_profit': round(float(tp), 5),
                'risk_reward': round(rr, 2),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[ERROR] {pair}: {e}", flush=True)
            return None

def main():
    print("=" * 60, flush=True)
    print("FOREX AI TRADING SYSTEM v1.0", flush=True)
    print("=" * 60, flush=True)
    
    trader = ForexAITrader()
    
    # Train model
    print("\n[TRAIN] Training Phase", flush=True)
    print("-" * 40, flush=True)
    
    # Try to train, but continue even if it fails
    try:
        trader.train_model('EURUSD=X', days=30)
    except Exception as e:
        print(f"[TRAIN] Skipping training: {e}", flush=True)
    
    # Get signals
    print("\n[SIGNALS] Live Signals", flush=True)
    print("-" * 40, flush=True)
    
    signals = []
    for pair in trader.pairs:
        try:
            signal = trader.get_signal(pair)
            if signal:
                signals.append(signal)
                print(f"\n{signal['pair']}:", flush=True)
                print(f"  {signal['signal']} ({signal['strength']}) - {signal['confidence']:.0%} confidence", flush=True)
                print(f"  Entry: {signal['entry']} | SL: {signal['stop_loss']} | TP: {signal['take_profit']}", flush=True)
            else:
                print(f"\n{pair.replace('=X', '')}: WAIT", flush=True)
        except Exception as e:
            print(f"\n{pair.replace('=X', '')}: ERROR - {e}", flush=True)
    
    # Output JSON for backend
    print("\n" + "=" * 60, flush=True)
    print(json.dumps(signals, indent=2), flush=True)

if __name__ == "__main__":
    main()