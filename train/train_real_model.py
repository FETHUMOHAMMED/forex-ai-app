"""
TRAIN XGBOOST WITH ATR‑NORMALIZED STRUCTURAL TARGET (MT5 H1)
- Target: BUY if 6‑hour forward move > 1.5 * current ATR (in price terms)
          SELL if move < -1.5 * ATR
          else hold (NaN)
- Features: ICT patterns, session dummies, H4 EMA distance, volatility regime
- Regularised model to prevent overfitting
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from risk.features import FEATURE_COLUMNS
from sklearn.model_selection import TimeSeriesSplit
from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV
import joblib
import MetaTrader5 as mt5
from datetime import datetime

class RealMLTrainer:
    def __init__(self):
        self.pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'USDSGD']

    def _find_symbol(self, pair):
        for suffix in ['', 'm', '.', 'pro']:
            if mt5.symbol_select(pair + suffix, True):
                return pair + suffix
        return None

    def fetch_data_mt5(self, pair, start, end):
        symbol = self._find_symbol(pair)
        if not symbol:
            return None
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1,
                                     pd.to_datetime(start),
                                     pd.to_datetime(end))
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        return df[['open', 'high', 'low', 'close', 'volume']]

    def add_features(self, df):
        """Add technical indicators, ICT patterns, H4 distance, session dummies, and ATR‑normalized target."""
        # Basic returns
        df['returns'] = df['close'].pct_change()
        df['high_low_ratio'] = (df['high'] - df['low']) / df['close']

        # RSI
        delta = df['close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        e12 = df['close'].ewm(span=12, adjust=False).mean()
        e26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = e12 - e26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # Bollinger
        df['bb_mid'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2*df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2*df['bb_std']

        # ATR
        h_l = df['high'] - df['low']
        h_c = (df['high'] - df['close'].shift()).abs()
        l_c = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([h_l, h_c, l_c], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()

        # Volume ratio
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

        # ---------- ICT-derived features ----------
        # FVG
        df['fvg_buy'] = (df['high'].shift(2) < df['low']).astype(int)
        df['fvg_sell'] = (df['low'].shift(2) > df['high']).astype(int)
        # Order block
        df['ob_buy'] = ((df['low'] > df['low'].shift(1)) &
                        (df['low'].shift(1) > df['low'].shift(2))).astype(int)
        df['ob_sell'] = ((df['high'] < df['high'].shift(1)) &
                         (df['high'].shift(1) < df['high'].shift(2))).astype(int)
        # MSS
        swing_high = df['high'].rolling(5).max().shift(1)
        swing_low = df['low'].rolling(5).min().shift(1)
        df['mss_buy'] = ((df['close'] > swing_high) &
                         (df['close'].shift(1) <= swing_high)).astype(int)
        df['mss_sell'] = ((df['close'] < swing_low) &
                          (df['close'].shift(1) >= swing_low)).astype(int)

        # ---------- H4 EMA distance (no look‑ahead) ----------
        h4_close = df['close'].resample('4h').last()
        h4_close_prev = h4_close.shift(1)                      # use previous completed candle
        h4_ema200 = h4_close_prev.ewm(span=200, min_periods=200).mean()
        df['h4_ema200'] = h4_ema200.reindex(df.index, method='ffill')
        df['dist_from_h4_ema'] = (df['close'] - df['h4_ema200']) / df['h4_ema200'] * 100
        df['h4_uptrend']   = (df['close'] > df['h4_ema200']).astype(int)
        df['h4_downtrend'] = (df['close'] < df['h4_ema200']).astype(int)
        # H4 trend dummies
        df['h4_uptrend']   = (df['close'] > df['h4_ema200']).astype(int)
        df['h4_downtrend'] = (df['close'] < df['h4_ema200']).astype(int)

        # Asian session
        df['asian'] = ((hours >= 0) & (hours < 7)).astype(int)

        # Continuous volatility percentile
        df['atr_percentile'] = df['atr'].rolling(200).rank(pct=True)

        # ---------- Session dummies ----------
        hours = df.index.hour
        df['london'] = ((hours >= 7) & (hours < 12)).astype(int)
        df['newyork'] = ((hours >= 13) & (hours < 18)).astype(int)

        # ---------- Volatility regime ----------
        atr_long = df['atr'].rolling(200).median()
        df['vol_high'] = (df['atr'] > atr_long * 1.5).astype(int)

        # ========== NEW ATR‑NORMALIZED TARGET ==========
        # 6‑hour forward absolute price move (not percentage)
        df['future_move'] = df['close'].shift(-6) - df['close']

        # Use current ATR (in price units) as threshold
        # BUY if move > 1.5 * ATR, SELL if move < -1.5 * ATR, else NaN
        df['target'] = np.where(
            df['future_move'] > df['atr'] * 1.5,
            1,
            np.where(df['future_move'] < -df['atr'] * 1.5, 0, np.nan)
        )

        # Drop rows where target is NaN (noise / small moves)
        df = df.dropna(subset=['target'])
        df['target'] = df['target'].astype(int)

        return df.dropna()

    def train_model(self, pair):
        print(f"\n{'='*50}")
        print(f"Training on {pair}")
        print('='*50)

        # USE MORE DATA: 2018 to now
        start = '2018-01-01'
        end = datetime.now().strftime('%Y-%m-%d')
        df = self.fetch_data_mt5(pair, start, end)
        if df is None or len(df) < 500:
            print(f"❌ Not enough data for {pair}")
            return None, 0.0

        df = self.add_features(df)
        print(f"   Data points after ATR target: {len(df)}")

        features = FEATURE_COLUMNS

        X = df[features].fillna(0)
        y = df['target']

        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        # Small, regularised model
        model = xgb.XGBClassifier(
            n_estimators=80,
            max_depth=3,
            learning_rate=0.03,
            subsample=0.7,
            colsample_bytree=0.7,
            reg_alpha=2.0,
            reg_lambda=3.0,
            random_state=42
        )
        model.fit(X_train, y_train)

        # ---- Feature importance (raw model, before calibration) ----
        imp_values = model.feature_importances_
        importance = dict(zip(features, imp_values))
        print("   Top 5 Features:")
        for feat, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"      {feat}: {imp:.3f}")

        # ---- Full feature importance list (from the calibrated model) ----
        if hasattr(calibrated, 'estimator_'):
            base_imp = calibrated.estimator_.feature_importances_
        else:
            base_imp = imp_values   # fallback if calibration fails
        print("   All Features (calibrated):")
        for name, score in zip(features, base_imp):
            print(f"      {name}: {score:.3f}")

        # Calibrate with time‑series aware cross‑validation (no future leakage)
        
        tscv = TimeSeriesSplit(n_splits=3)
        calibrator = CalibratedClassifierCV(estimator=model, method='isotonic', cv=tscv)
        calibrator.fit(X_train, y_train)
        calibrated = calibrator

        train_acc = calibrated.score(X_train, y_train)
        test_acc = calibrated.score(X_test, y_test)
        print(f"   Training Accuracy: {train_acc:.2%}")
        print(f"   Test Accuracy:     {test_acc:.2%}")

        filename = f"models/{pair}_xgboost.joblib"
        joblib.dump(calibrated, filename)
        print(f"   ✅ Calibrated model saved to {filename}")
        return calibrated, test_acc
    
        # --- Quick risk metrics on the test set (for informational purposes) ---
        try:
            test_preds = calibrated.predict_proba(X_test)[:, 1]
            # Simulate simple SL/TP with the average ATR on the test set
            avg_atr = df['atr'].iloc[-len(X_test):].mean()
            sl_mult, tp_mult = 1.5, 2.5
            trades = []
            for i, (true_price, future_close) in enumerate(zip(
                df['close'].iloc[-len(X_test):].values,
                df['close'].shift(-1).iloc[-len(X_test):].values
            )):
                pred = test_preds[i]
                if pred > 0.55:   # only trade if confidence > 55%
                    direction = 1   # BUY
                    pnl = (future_close - true_price) * 10000  # simplified
                    trades.append(pnl)
                elif pred < 0.45:
                    direction = -1  # SELL
                    pnl = (true_price - future_close) * 10000
                    trades.append(pnl)
            if trades:
                trades = np.array(trades)
                gp = trades[trades > 0].sum()
                gl = abs(trades[trades < 0].sum())
                pf = gp / gl if gl > 0 else float('inf')
                wr = (trades > 0).mean()
                print(f"   Sample PF (test): {pf:.2f}, WR: {wr:.1%}, Trades: {len(trades)}")
        except Exception:
            pass

def main():
    print("=" * 60)
    print("TRAINING ATR‑NORMALIZED STRUCTURAL ML MODELS")
    print("=" * 60)

    if not mt5.initialize():
        print("❌ MT5 not running.")
        return

    trainer = RealMLTrainer()
    results = {}
    for pair in trainer.pairs:
        _, acc = trainer.train_model(pair)
        if acc is not None:
            results[pair] = acc

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE!")
    for pair, acc in results.items():
        print(f"   {pair}: {acc:.2%} test accuracy")
    print("✅ Calibrated models ready for GA evolution.")

if __name__ == "__main__":
    main()