"""COMPLETE PAPER SYSTEM - Fixed data retrieval."""
import MetaTrader5 as mt5
import pandas as pd
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

class CompletePaperSystem:
    def __init__(self):
        self.log_file = Path("research/paper/V4_CANONICAL_1.0/complete_evaluation_log.jsonl")
        self.strategy_version = "V4_CANONICAL_1.0"
    
    def evaluate_complete(self):
        if not mt5.initialize():
            return self.log_result({"decision": "ERROR", "reason": "MT5_INIT_FAILED"})
        
        # Try multiple methods to get data
        rates = None
        
        # Method 1: copy_rates_from_pos
        rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 200)
        
        # Method 2: copy_rates_range (last 40 days)
        if rates is None or len(rates) == 0:
            now = datetime.now()
            start = now - timedelta(days=40)
            rates = mt5.copy_rates_range("USDJPYm", mt5.TIMEFRAME_H4, start, now)
        
        # Method 3: Use tick data as fallback
        if rates is None or len(rates) == 0:
            tick = mt5.symbol_info_tick("USDJPYm")
            if tick:
                mt5.shutdown()
                result = {
                    "decision": "NO_DATA_FOR_BACKTEST",
                    "reason": "Only tick data available",
                    "current_price": tick.bid,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "strategy_version": self.strategy_version,
                    "symbol": "USDJPYm"
                }
                self.display_result(result)
                return self.log_result(result)
        
        mt5.shutdown()
        
        if rates is None or len(rates) < 50:
            result = {"decision": "ERROR", "reason": "INSUFFICIENT_DATA"}
            self.display_result(result)
            return self.log_result(result)
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        # Calculate indicators
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean() if len(data) >= 200 else data['close'].ewm(span=50).mean()
        
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        
        last = data.iloc[-1]
        candle_1 = data.iloc[-3] if len(data) >= 3 else data.iloc[0]
        
        # Check conditions
        fvg_detected = candle_1['high'] < last['low']
        bullish_bias = last['ema_50'] > last['ema_200']
        current_hour = datetime.now(timezone.utc).hour
        london_session = 7 <= current_hour < 11
        
        sl = None
        tp = None
        if fvg_detected and bullish_bias:
            sl = last['close'] - (last['atr'] * 2.0)
            tp = last['close'] + (last['atr'] * 4.0)
        
        if fvg_detected and bullish_bias and london_session:
            decision = "TRADE"
            reason = "VALID_BUY_SETUP"
        elif not fvg_detected:
            decision = "REJECT"
            reason = "NO_FVG"
        elif not bullish_bias:
            decision = "REJECT"
            reason = "BEARISH_BIAS"
        elif not london_session:
            decision = "REJECT"
            reason = "OUTSIDE_LONDON"
        else:
            decision = "REJECT"
            reason = "UNKNOWN"
        
        result = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "strategy_version": self.strategy_version,
            "symbol": "USDJPYm",
            "timeframe": "H4",
            "current_price": last['close'],
            "atr": last['atr'] if pd.notna(last['atr']) else None,
            "ema_50": last['ema_50'],
            "ema_200": last['ema_200'],
            "bias": "BULLISH" if bullish_bias else "BEARISH",
            "fvg_detected": bool(fvg_detected),
            "fvg_candle_1_high": candle_1['high'],
            "fvg_candle_3_low": last['low'],
            "fvg_size": last['low'] - candle_1['high'] if fvg_detected else 0,
            "session": "LONDON" if london_session else "OTHER",
            "current_hour_utc": current_hour,
            "direction": "BUY",
            "risk_percent": 0.25,
            "sl": sl,
            "tp": tp,
            "rr_ratio": 2.0 if sl and tp else None,
            "decision": decision,
            "reason": reason,
            "bars_count": len(data)
        }
        
        self.display_result(result)
        return self.log_result(result)
    
    def log_result(self, result):
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(result) + '\n')
        return result
    
    def display_result(self, result):
        print("="*70)
        print("  COMPLETE PAPER EVALUATION")
        print("="*70)
        for key, value in result.items():
            print(f"  {key}: {value}")
        print("="*70)
    
    def run_once(self):
        return self.evaluate_complete()

if __name__ == "__main__":
    system = CompletePaperSystem()
    system.run_once()
