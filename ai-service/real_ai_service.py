"""
REAL FOREX AI SERVICE -- Live Market Data (MT5 primary, Yahoo fallback)
Includes:
- Multi-Timeframe Trend Filter (H1 EMA50 slope)
- Volatility Filter (ATR range)
- Enhanced ICT Patterns (BB, LV, MSS)
- Relaxed ensemble thresholds
- Mock signal fallback with real price data
- Backtest helper: get_signal_from_row (no live data fetch)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import warnings
import logging
import time
from institutional.liquidity_intelligence import LiquidityIntelligence
from institutional.institutional_structure import InstitutionalStructure
from institutional.performance_intelligence import PerformanceIntelligence
from datetime import datetime, timezone
from risk.features import FEATURE_COLUMNS
import numpy as np
import pandas as pd
import yfinance as yf
import joblib
from dotenv import load_dotenv


# Institutional intelligence
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from institutional.market_microstructure import MarketMicrostructure

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)-5s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('forex_ai.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('signal_engine')
warnings.filterwarnings('ignore')

class RealAITrader:
    def __init__(self):
        self.models = {}
        # Volume 9.5 blocked pairs
        self.blocked_pairs = {'USDJPY','USDCAD','NZDUSD','USDCHF','USDSGD','AUDUSD','EURJPY','GBPJPY','EURGBP','AUDJPY'}
        demo2_pairs = ['EURUSD','GBPUSD','USDJPY','USDCAD','NZDUSD','AUDUSD','EURJPY','GBPJPY','EURGBP','AUDJPY']
        self.pairs = CONFIG.get('pairs', demo2_pairs)
        self.yahoo_symbols = {
            'EURUSD': 'EURUSD=X', 'GBPUSD': 'GBPUSD=X', 'USDJPY': 'USDJPY=X',
            'AUDUSD': 'AUDUSD=X', 'USDCAD': 'USDCAD=X', 'USDCHF': 'USDCHF=X',
            'NZDUSD': 'NZDUSD=X', 'USDSGD': 'USDSGD=X'
        }
        self.timeframe = '15m'
        self.lookback_days = 5
        self._load_models()
        self.microstructure = MarketMicrostructure()
        self.liquidity_engine = LiquidityIntelligence()
        self.structure_engine = InstitutionalStructure()
        self.performance_engine = PerformanceIntelligence()
        self.use_mock_fallback = False

        if MT5_AVAILABLE:
            self.mt5_timeframe = mt5.TIMEFRAME_M15
            self.mt5_timeframe_h1 = mt5.TIMEFRAME_H1
        else:
            self.mt5_timeframe = None
            self.mt5_timeframe_h1 = None
            self.strict_mode = False   # set to True for live accounts
            
        # Rejection tracking
        self.rejected_trend = 0
        self.rejected_no_ict = 0
        self.rejected_low_conf = 0
        self.accepted = 0

    def _load_models(self):
        models_dir = os.path.join(os.path.dirname(__file__), 'models')
        for pair in self.pairs:
            if pair in self.blocked_pairs:
                continue
            model_path = os.path.join(models_dir, f'{pair}_xgboost.joblib')
            if os.path.exists(model_path):
                try:
                    self.models[pair] = joblib.load(model_path)
                    logger.info(f"[OK] Loaded model for {pair}")
                except Exception as e:
                    logger.error(f"Failed to load {pair}: {e}")
                    self.models[pair] = None
            else:
                logger.warning(f"[WARN] No model for {pair}")
                self.models[pair] = None

    def _init_mt5(self):
        """Initialize MT5 and ensure all trading symbols are available"""
        if not MT5_AVAILABLE:
            return False
        import MetaTrader5 as mt5
        if mt5.terminal_info() is None and not mt5.initialize():
            logger.error(f"MT5 init failed: {mt5.last_error()}")
            return False
        
        # Ensure all symbols are in Market Watch
        for pair in self.pairs:
            for suffix in ['m', '']:
                symbol = pair + suffix
                try:
                    mt5.symbol_select(symbol, True)
                except:
                    pass
        
        return True

    def _get_mt5_symbol(self, pair):
        """Find the actual MT5 symbol name via broker layer."""
        if not MT5_AVAILABLE or not self._init_mt5():
            return None
        # Try common suffixes via broker's symbol_select
        import MetaTrader5 as mt5
        for suffix in ['', 'm', '.', 'pro']:
            symbol = pair + suffix
            if mt5.symbol_select(symbol, True):
                return symbol
        return None

    def fetch_data_mt5(self, pair, bars=500, timeframe=None):
        if not MT5_AVAILABLE:
            return None
        if not self._init_mt5():
            return None
        if timeframe is None:
            timeframe = self.mt5_timeframe
        
        import MetaTrader5 as mt5
        
        try:
            symbol = self._get_mt5_symbol(pair)
            if not symbol:
                logger.warning(f"No MT5 symbol for {pair}")
                return None
            
            fetch_start = time.time()
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
            fetch_time = time.time() - fetch_start
            
            if fetch_time > 0.5:
                logger.warning(f"Slow MT5: {pair} took {fetch_time:.2f}s")
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No rates from MT5 for {pair}")
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df.columns = ['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
            df['volume'] = df['tick_volume']
            return df[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"MT5 fetch error {pair}: {e}")
            return None

    def get_higher_tf_trend(self, pair):
        df = self.fetch_data_mt5(pair, bars=500, timeframe=self.mt5_timeframe_h1)
        if df is None or len(df) < 100:
            logger.warning(f"Insufficient H1 data for {pair}, trend = NEUTRAL")
            return 'NEUTRAL'
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        slope = df['ema50'].iloc[-1] - df['ema50'].iloc[-10]
        ema_bullish = df['ema50'].iloc[-1] > df['ema200'].iloc[-1]
        if slope > 0 and ema_bullish:
            return 'BULLISH'
        elif slope < 0 and not ema_bullish:
            return 'BEARISH'
        else:
            return 'NEUTRAL'

    def fetch_data_yahoo(self, pair, retries=2):
        symbol = self.yahoo_symbols.get(pair)
        for attempt in range(retries):
            try:
                df = yf.download(symbol, period=f'{self.lookback_days}d',
                                 interval=self.timeframe, progress=False, auto_adjust=False)
                if df.empty:
                    logger.warning(f"Yahoo empty for {pair}")
                    time.sleep(2)
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
                else:
                    df.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
                return df
            except Exception as e:
                logger.error(f"Yahoo error {pair}: {e}")
                time.sleep(2)
        return None

    def fetch_data(self, pair):
        df = self.fetch_data_mt5(pair)
        if df is not None and len(df) >= 50:
            logger.info(f"[DATA] MT5 data for {pair}: {len(df)} bars")
            return df
        logger.warning(f"[WARN] MT5 failed for {pair} -- no data available")
        return None

    def add_indicators(self, df):
        if df is None or len(df) < 50:
            return None
        df = df.copy()

        df['returns'] = df['close'].pct_change()
        df['high_low_ratio'] = (df['high'] - df['low']) / df['close']

        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        df['bb_mid'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()

        vol_mean = df['volume'].rolling(20).mean()
        df['volume_ratio'] = (df['volume'] / vol_mean.replace(0, np.nan)).fillna(1)

        df['fvg_buy'] = (df['high'].shift(2) < df['low']).astype(int)
        df['fvg_sell'] = (df['low'].shift(2) > df['high']).astype(int)
        df['ob_buy'] = ((df['low'] > df['low'].shift(1)) &
                        (df['low'].shift(1) > df['low'].shift(2))).astype(int)
        df['ob_sell'] = ((df['high'] < df['high'].shift(1)) &
                         (df['high'].shift(1) < df['high'].shift(2))).astype(int)

        # Enhanced ICT
        df['bb_buy'] = ((df['low'].shift(1) < df['low'].shift(2)) &
                        (df['high'] > df['high'].shift(1)) &
                        (df['close'] > df['high'].shift(1))).astype(int)
        df['bb_sell'] = ((df['high'].shift(1) > df['high'].shift(2)) &
                         (df['low'] < df['low'].shift(1)) &
                         (df['close'] < df['low'].shift(1))).astype(int)

        df['lv_buy'] = (df['low'] > df['high'].shift(1)).astype(int)
        df['lv_sell'] = (df['high'] < df['low'].shift(1)).astype(int)

        swing_high = df['high'].rolling(5).max().shift(1)
        swing_low = df['low'].rolling(5).min().shift(1)
        df['mss_buy'] = ((df['close'] > swing_high) & (df['close'].shift(1) <= swing_high)).astype(int)
        df['mss_sell'] = ((df['close'] < swing_low) & (df['close'].shift(1) >= swing_low)).astype(int)

        df = df.dropna()
        return df
    
    
    # -----------------------------------------------------------------
    # Backtest helper -- signal from a single precomputed row
    # -----------------------------------------------------------------
    def get_signal_from_row(self, row, pair, use_filters=True,
                            atr_min=0.0005, atr_max=0.003,
                            atr_min_jpy=0.05, atr_max_jpy=0.3):
        """Generate a signal from a precomputed indicator row (for backtesting)."""
        latest = row
        current_price = float(latest['close'])
        atr = float(latest['atr']) if 'atr' in latest else current_price * 0.0015

        if use_filters:
            if 'JPY' in pair:
                if atr < atr_min_jpy or atr > atr_max_jpy:
                    return None
            else:
                if atr < atr_min or atr > atr_max:
                    return None

        model = self.models.get(pair)
        ml_signal = None
        ml_conf = 0.5
        if model is not None:
            feature_cols = FEATURE_COLUMNS
            try:
                X = pd.DataFrame([latest[feature_cols].fillna(0).values], columns=feature_cols)
                proba = model.predict_proba(X)[0]
                pred = model.predict(X)[0]
                ml_signal = 'BUY' if pred == 1 else 'SELL'
                ml_conf = float(proba[1] if pred == 1 else proba[0])
            except:
                pass

        signal = None
        confidence = 0.5
        
        # Same weighted ICT as live (MSS=3, OB=3, FVG=2, BB=2, LV=1)
        buy_score = (latest.get('mss_buy', 0) * 3 + latest.get('ob_buy', 0) * 3 +
                     latest.get('fvg_buy', 0) * 2 + latest.get('bb_buy', 0) * 2 +
                     latest.get('lv_buy', 0) * 1)
        sell_score = (latest.get('mss_sell', 0) * 3 + latest.get('ob_sell', 0) * 3 +
                      latest.get('fvg_sell', 0) * 2 + latest.get('bb_sell', 0) * 2 +
                      latest.get('lv_sell', 0) * 1)
        
        ict_buy = buy_score >= 5  # lowered for data collection
        logger.info(f"[ICT DEBUG] {pair}: buy_score={buy_score} sell_score={sell_score} MSS_b={latest.get('mss_buy',0)} OB_b={latest.get('ob_buy',0)} FVG_b={latest.get('fvg_buy',0)} MSS_s={latest.get('mss_sell',0)} OB_s={latest.get('ob_sell',0)}")
        ict_sell = sell_score >= 5  # lowered for data collection
        
        # Same ensemble as live
        if ict_buy and ml_signal == 'BUY':
            signal = 'BUY'; confidence = ml_conf
        elif ict_sell and ml_signal == 'SELL':
            signal = 'SELL'; confidence = ml_conf
        elif ml_signal and ml_conf >= 0.58 and not ict_buy and not ict_sell and pair in {'USDCHF', 'USDJPY'}:
            signal = ml_signal; confidence = ml_conf * 0.95

        if not signal:
            return None

        sl_mult, tp_mult = 1.5, 2.5
        if signal == 'BUY':
            sl = current_price - atr * sl_mult
            tp = current_price + atr * tp_mult
        else:
            sl = current_price + atr * sl_mult
            tp = current_price - atr * tp_mult

        return {
            'pair': pair,
            'signal': signal,
            'confidence': confidence,
            'entry': current_price,
            'stop_loss': sl,
            'take_profit': tp
        }

    def get_mock_signal(self, pair):
        import random
        random.seed(hash(pair) + datetime.now().minute)

        df = self.fetch_data(pair)
        if df is not None and len(df) > 0:
            current_price = float(df['close'].iloc[-1])
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1] if len(tr) >= 14 else current_price * 0.0015
        else:
            base_prices = {'EURUSD': 1.0925, 'GBPUSD': 1.2650, 'USDJPY': 148.50,
                           'AUDUSD': 0.6580, 'USDCAD': 1.3540}
            current_price = base_prices.get(pair, 1.0)
            atr = current_price * 0.0015

        signal = 'BUY' if random.random() > 0.4 else 'SELL'
        confidence = round(random.uniform(0.65, 0.85), 3)
        strength = 'STRONG' if confidence > 0.75 else 'MEDIUM' if confidence > 0.65 else 'WEAK'

        sl_mult, tp_mult = 1.5, 2.5
        if signal == 'BUY':
            sl = current_price - atr * sl_mult
            tp = current_price + atr * tp_mult
        else:
            sl = current_price + atr * sl_mult
            tp = current_price - atr * tp_mult

        return {
            'pair': pair,
            'signal': signal,
            'confidence': confidence,
            'strength': strength,
            'entry': round(current_price, 5),
            'stop_loss': round(sl, 5),
            'take_profit': round(tp, 5),
            'risk_reward': round(abs(tp - current_price) / abs(sl - current_price), 2),
            'timestamp': datetime.now().isoformat()
        }

    def get_signal(self, pair):
        """Get a signal with fallback to mock signal."""
        real = self.get_real_signal(pair)
        if real:
            logger.info(f"[OK] Real signal for {pair}: {real['signal']} ({real['confidence']:.0%})")
            return real
        elif self.use_mock_fallback:
            mock = self.get_mock_signal(pair)
            logger.info(f"[LOOP] Using mock signal for {pair}")
            return mock
        return None
    
    def get_real_signal(self, pair):
        df = self.fetch_data(pair)
        if df is None:
            logger.warning(f"No data for {pair}")
            return None
        
        # === PHASE 2: Institutional Microstructure Analysis (Observation Only) ===
        if len(df) >= 20:
            ms_result = self.microstructure.analyze(pair, df)
            logger.info(f"[INSTITUTIONAL] {pair}: {ms_result.institutional_bias} "
                       f"(score={ms_result.microstructure_score}) "
                       f"dealer={ms_result.dealer_pressure} "
                       f"liquidity={ms_result.liquidity_state} "
                       f"continuation={ms_result.continuation_probability:.0%}")
            
        # === VOLUME 2: Liquidity Intelligence ===
        if len(df) >= 50:
            liq_result = self.liquidity_engine.analyze(pair, df)
            logger.info(f"[LIQUIDITY] {pair}: nearest={liq_result.nearest_liquidity} "
                       f"distance={0} "
                       f"sweep_prob={liq_result.sweep_strength:.0%} "
                       f"inst_interest={str(liq_result.sweep_direction or "NONE")} "
                       f"score={liq_result.liquidity_score:.0f}") 
            
        # === VOLUME 3: Institutional Structure Intelligence ===
        if len(df) >= 100:
            struct_result = self.structure_engine.analyze(pair, df)
            logger.info(f"[STRUCTURE] {pair}: phase={struct_result.market_phase} "
                       f"bias={struct_result.structure_bias} score={struct_result.structure_score:.0f} "
                       f"trend={"UNKNOWN"} expansion={"UNKNOWN"} "
                       f"cycle={"UNKNOWN"} continuation={struct_result.continuation_probability:.0%}")       
        
        # === VOLUME 7: Performance Intelligence ===
        if len(df) >= 50:
            try:
                session = 'LONDON' if 7 <= datetime.now(timezone.utc).hour < 13 else 'ASIAN'
                perf = self.performance_engine.analyze_setup(
                    pair, signal if signal else 'NEUTRAL', session,
                    liquidity_state=liq_result.liquidity_state if 'liq_result' in dir() else None,
                    structure_phase=struct_result.market_phase if 'struct_result' in dir() else None
                )
                if signal and perf.edge_score > 60:
                    logger.info(f"[PERFORMANCE] {pair}: edge={perf.edge_score:.0f} "
                               f"similar={perf.similar_trades} hist_wr={perf.historical_win_rate:.0f}% "
                               f"best_setup={perf.best_setup} rec={perf.risk_recommendation}")
            except:
                pass
        
        df = self.add_indicators(df)
        if df is None or len(df) < 10:
            logger.warning(f"Insufficient indicator data for {pair}")
            return None

        # Compute H4 EMA using ONLY completed 4‑hour candles (no future leakage)
        h4_close = df['close'].resample('4h').last().ffill()
        h4_close_prev = h4_close.shift(1)
        h4_ema200 = h4_close_prev.ewm(span=200, min_periods=200).mean()
        df['h4_ema200'] = h4_ema200.reindex(df.index, method='ffill')
        df['dist_from_h4_ema'] = (df['close'] - df['h4_ema200']) / df['h4_ema200'] * 100
        df['h4_uptrend']   = (df['close'] > df['h4_ema200']).astype(int)
        df['h4_downtrend'] = (df['close'] < df['h4_ema200']).astype(int)

        hours = df.index.hour
        df['london'] = ((hours >= 7) & (hours < 12)).astype(int)
        df['newyork'] = ((hours >= 13) & (hours < 18)).astype(int)
        df['asian']   = ((hours >= 0) & (hours < 7)).astype(int)

        atr_long = df['atr'].rolling(200).median()
        df['vol_high'] = (df['atr'] > atr_long * 1.5).astype(int)
        df['atr_percentile'] = df['atr'].rolling(200, min_periods=200).rank(pct=True)

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        current_price = float(latest['close'])
        atr = float(latest['atr']) if 'atr' in latest else current_price * 0.0015

        # ATR range filter
        if CONFIG.get('use_filters', True):
            if pair in ('XAUUSD', 'XAUUSDm', 'GOLD'):
                atr_min, atr_max = 5.0, 50.0
            elif pair in ('XAGUSD', 'XAGUSDm', 'SILVER'):
                atr_min, atr_max = 0.1, 2.0
            elif 'JPY' in pair:
                atr_min = CONFIG.get('atr_min_jpy', 0.01)
                atr_max = CONFIG.get('atr_max_jpy', 5.0)
            else:
                atr_min = CONFIG.get('atr_min_non_jpy', 0.0001)
                atr_max = CONFIG.get('atr_max_non_jpy', 0.05)
            if atr < atr_min or atr > atr_max:
                logger.info(f"[SKIP] Signal skipped: ATR ({atr:.5f}) outside range ({atr_min}--{atr_max})")
                return None

        feature_cols = FEATURE_COLUMNS
        for col in feature_cols:
            if col not in latest.index:
                latest[col] = 0.0

        # ---- LAYER 1: ICT Weighted Scoring ----
        buy_score = (prev.get('mss_buy', 0) * 3 + prev.get('ob_buy', 0) * 3 +
                     prev.get('fvg_buy', 0) * 2 + prev.get('bb_buy', 0) * 2 +
                     prev.get('lv_buy', 0) * 1)
        sell_score = (prev.get('fvg_sell', 0) * 2 + prev.get('ob_sell', 0) * 3 +
                      prev.get('bb_sell', 0) * 1 + prev.get('lv_sell', 0) * 1 +
                      prev.get('mss_sell', 0) * 2)
        
        ict_buy = buy_score >= 5
        ict_sell = sell_score >= 5
        
        if ict_buy and ict_sell:
            if buy_score > sell_score:
                ict_sell = False
            elif sell_score > buy_score:
                ict_buy = False
            else:
                ict_buy = False
                ict_sell = False

        # ---- LAYER 2: ML Prediction ----
        model = self.models.get(pair)
        ml_signal = None
        ml_conf = 0.5
        
        if model is not None:
            X = pd.DataFrame([latest[feature_cols].fillna(0).values], columns=feature_cols)
            try:
                proba = model.predict_proba(X)[0]
                pred = model.predict(X)[0]
                ml_signal = 'BUY' if pred == 1 else 'SELL'
                ml_conf = float(proba[1] if pred == 1 else proba[0])
                logger.info(f"ML for {pair}: {ml_signal} conf={ml_conf:.3f}")
            except Exception as e:
                logger.error(f"Prediction error {pair}: {e}")
                ml_signal = None
                ml_conf = 0.5
        else:
            ml_signal = None
            ml_conf = 0.5

        logger.info(f"ICT for {pair}: buy={ict_buy}, sell={ict_sell}")

        # ---- LAYER 3: ML + ICT Must Agree ----
        signal = None
        strength = 'WEAK'
        confidence = 0.5

        if ict_buy and ml_signal == 'BUY':
            signal = 'BUY'
            strength = 'STRONG' if ml_conf > 0.55 else 'MEDIUM'
            confidence = ml_conf
        elif ict_sell and ml_signal == 'SELL':
            signal = 'SELL'
            strength = 'STRONG' if ml_conf > 0.55 else 'MEDIUM'
            confidence = ml_conf

        print(f"[SIGNAL DEBUG] {pair}: ml_sig={ml_signal}, ml_conf={ml_conf:.3f}, "
              f"ict_buy={ict_buy}, ict_sell={ict_sell}, signal={signal}", file=sys.stderr)

        if not signal:
            print(f"[SIGNAL DEBUG] {pair}: NO SIGNAL -- returning None", file=sys.stderr)
            self.rejected_no_ict += 1
            return None

        # ---- LAYER 4: Multi-Timeframe Confirmation ----
        # H4 trend check
        h4_uptrend = bool(latest.get('h4_uptrend', 0))
        h4_downtrend = bool(latest.get('h4_downtrend', 0))
        
        # H1 trend check
        trend = self.get_higher_tf_trend(pair)
        
        # Multi-TF alignment bonus/penalty
        if h4_uptrend and trend == 'BULLISH' and signal == 'BUY':
            confidence *= 1.05
            logger.info(f"Multi-TF aligned {pair}: H4-up H1-up signal=BUY")
        elif h4_downtrend and trend == 'BEARISH' and signal == 'SELL':
            confidence *= 1.05
            logger.info(f"Multi-TF aligned {pair}: H4-down H1-down signal=SELL")
        elif h4_uptrend and signal == 'SELL':
            confidence *= 0.85
            logger.info(f"H4 contradicts {pair}: H4 uptrend vs SELL signal")
        elif h4_downtrend and signal == 'BUY':
            confidence *= 0.85
            logger.info(f"H4 contradicts {pair}: H4 downtrend vs BUY signal")
        
        # H1 trend filter
        if trend != 'NEUTRAL':
            if (signal == 'BUY' and trend == 'BEARISH') or (signal == 'SELL' and trend == 'BULLISH'):
                confidence *= 0.90
                logger.info(f"[WARN] Counter-trend {signal} {pair}: H1={trend}, conf adjusted to {confidence:.3f}")
            else:
                logger.info(f"[OK] Trend-aligned {signal} {pair}: H1={trend}")

        # ---- LAYER 5: Minimum Confidence ----
        if confidence < 0.50:
            logger.info(f"[ERROR] Signal rejected: {pair} confidence too low ({confidence:.3f})")
            self.rejected_trend += 1
            return None

        # ---- Simple SL/TP ----
        sl_mult, tp_mult = 2.5, 4.0

        if signal == 'BUY':
            sl = current_price - atr * sl_mult
            tp = current_price + atr * tp_mult
        else:
            sl = current_price + atr * sl_mult
            tp = current_price - atr * tp_mult

        risk_distance = abs(sl - current_price)
        rr = round(abs(tp - current_price) / risk_distance, 2) if risk_distance > 0 else 0.0
        self.accepted += 1

        # Attach institutional microstructure data
        inst_data = {}
        if hasattr(self, 'microstructure') and df is not None and len(df) >= 20:
            try:
                ms = self.microstructure.analyze(pair, df)
                inst_data = {
                    'institutional_bias': ms.institutional_bias,
                    'institutional_score': ms.microstructure_score,
                    'dealer_pressure': ms.dealer_pressure,
                    'liquidity_state': ms.liquidity_state,
                    'continuation_prob': ms.continuation_probability,
                    'manipulation_prob': ms.manipulation_probability,
                    'expansion_quality': ms.expansion_quality,
                    'price_discovery': ms.price_discovery
                }
            except Exception as e:
                logger.debug(f"Institutional analysis skipped for {pair}: {e}")
        
        # RULE: Reject if institutional score < 55
        inst_score_check = inst_data.get('institutional_score', 0) if inst_data else 0
        if inst_score_check is not None and inst_score_check < 55:
            return None
        # Reject RANGE_COMPRESSION
        if inst_data and inst_data.get('structure_bias') == 'RANGE_COMPRESSION':
            return None

        # RULE: Reject if institutional score < 55
        inst_score_check = inst_data.get('institutional_score', 0) if inst_data else 0
        if inst_score_check is not None and inst_score_check < 55:
            return None
        # Reject RANGE_COMPRESSION
        if inst_data and inst_data.get('structure_bias') == 'RANGE_COMPRESSION':
            return None

        return {
            'pair': pair,
            'signal': signal,
            'confidence': round(confidence, 3),
            'strength': strength,
            'entry': round(current_price, 5),
            'stop_loss': round(sl, 5),
            'take_profit': round(tp, 5),
            'atr': round(atr, 6),
            'risk_reward': rr,
            'timestamp': datetime.now().isoformat(),
            'regime': 'volatile',
            **inst_data
        }   

    
def market_is_open(symbol):
    """Return True if the latest tick for `symbol` is less than 5 minutes old."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False
    tick_time = datetime.fromtimestamp(tick.time, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    return (now - tick_time).total_seconds() < 300

def is_forex_market_open():
    """
    Check if the forex market is currently open by verifying
    that a major pair (EURUSD) has a fresh tick (< 5 min old).
    """
    return market_is_open('EURUSDm') or market_is_open('EURUSD')   
# Cooldown dict: { ticket: datetime_of_last_attempt }
LAST_CLOSE_ATTEMPT = {}

def close_expired_trades(max_hours=12, cooldown_minutes=15):
    """
    Close any open position held > max_hours, but only if the market is open
    and we haven't tried to close this ticket in the last `cooldown_minutes`.
    """
    if mt5.terminal_info() is None and not mt5.initialize():
        return

    positions = mt5.positions_get()
    if positions is None:
        return

    now = datetime.now(timezone.utc)
    cooldown_seconds = cooldown_minutes * 60

    for pos in positions:
        # ---- Market open check ----
        if not market_is_open(pos.symbol):
            logger.info(f" {pos.symbol} market closed -- skipping close attempt")
            continue

        # ---- Time‑based exit condition ----
        open_time = datetime.fromtimestamp(pos.time, tz=timezone.utc)
        age_hours = (now - open_time).total_seconds() / 3600
        if age_hours < max_hours:
            continue

        # ---- Cooldown per ticket ----
        last_try = LAST_CLOSE_ATTEMPT.get(pos.ticket)
        if last_try:
            elapsed = (now - last_try).total_seconds()
            if elapsed < cooldown_seconds:
                logger.debug(f"⏳ Ticket {pos.ticket} cooldown ({elapsed:.0f}s ago) -- skipping")
                continue

        # ---- Log attempt (with ticket) ----
        logger.info(f"[TIMEOUT] Closing ticket {pos.ticket} {pos.symbol} held {age_hours:.1f}h")

        # Update last attempt time
        LAST_CLOSE_ATTEMPT[pos.ticket] = now

        # ---- Execute close ----
        if pos.type == 0:   # BUY
            close_price = mt5.symbol_info_tick(pos.symbol).bid
            close_type = mt5.ORDER_TYPE_SELL
        else:               # SELL
            close_price = mt5.symbol_info_tick(pos.symbol).ask
            close_type = mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": pos.ticket,
            "price": close_price,
            "deviation": 10,
            "comment": "time_exit",
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Failed to close ticket {pos.ticket} {pos.symbol}: {result.comment}")
        else:
            logger.info(f"[OK] Closed ticket {pos.ticket} {pos.symbol}")
    

    

def main():
    trader = RealAITrader()
    signals = []
    for pair in trader.pairs:
        signal = trader.get_signal(pair)
        if signal:
            signals.append(signal)
    print(json.dumps(signals))

if __name__ == "__main__":
    main()



