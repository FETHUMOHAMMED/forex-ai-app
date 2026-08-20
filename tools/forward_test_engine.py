"""Forward Testing Engine - Runs validated strategy on demo."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import json
from datetime import datetime, timezone
from pathlib import Path
import time

class ForwardTestEngine:
    """Runs the validated FVG strategy in forward test mode."""
    
    def __init__(self):
        self.strategy = {
            "name": "FVG_H4_2.5R_London",
            "symbol": "USDJPYm",
            "timeframe": mt5.TIMEFRAME_H4,
            "session_start": 7,
            "session_end": 11,
            "ema_fast": 50,
            "ema_slow": 200,
            "atr_period": 14,
            "sl_atr_mult": 1.5,
            "tp_atr_mult": 3.75,
            "max_hold_bars": 50
        }
        
        self.results_dir = Path("research/forward_test/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.trades = []
        self.current_position = None
        self.position_bars_held = 0
        
    def check_for_setup(self):
        """Check if there's a valid FVG setup."""
        if not mt5.initialize():
            print(f"MT5 init failed: {mt5.last_error()}")
            return None
        
        # Get current H4 candle
        rates = mt5.copy_rates_from_pos(
            self.strategy["symbol"],
            self.strategy["timeframe"],
            0,
            200  # Need enough for EMA200
        )
        
        if rates is None or len(rates) < 200:
            print("Insufficient data")
            mt5.shutdown()
            return None
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        # Current time check
        current_hour = datetime.now(timezone.utc).hour
        if not (self.strategy["session_start"] <= current_hour < self.strategy["session_end"]):
            mt5.shutdown()
            return None
        
        # Calculate indicators
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean()
        
        # ATR
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        
        # Check FVG (last 3 bars)
        if len(data) < 3:
            mt5.shutdown()
            return None
        
        candle_1 = data.iloc[-3]  # Oldest
        candle_3 = data.iloc[-1]  # Current (just closed)
        
        # Bullish FVG
        bullish_bias = data['ema_50'].iloc[-1] > data['ema_200'].iloc[-1]
        
        if bullish_bias and candle_1['high'] < candle_3['low']:
            # Valid bullish FVG
            entry = candle_3['close']
            atr = data['atr'].iloc[-1]
            sl = entry - (atr * self.strategy["sl_atr_mult"])
            tp = entry + (atr * self.strategy["tp_atr_mult"])
            
            mt5.shutdown()
            return {
                "direction": "BUY",
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "atr": atr,
                "timestamp": candle_3['timestamp']
            }
        
        # Bearish FVG
        bearish_bias = data['ema_50'].iloc[-1] < data['ema_200'].iloc[-1]
        
        if bearish_bias and candle_1['low'] > candle_3['high']:
            entry = candle_3['close']
            atr = data['atr'].iloc[-1]
            sl = entry + (atr * self.strategy["sl_atr_mult"])
            tp = entry - (atr * self.strategy["tp_atr_mult"])
            
            mt5.shutdown()
            return {
                "direction": "SELL",
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "atr": atr,
                "timestamp": candle_3['timestamp']
            }
        
        mt5.shutdown()
        return None
    
    def execute_paper_trade(self, setup):
        """Execute trade on paper (no real order)."""
        trade = {
            "id": len(self.trades) + 1,
            "entry_time": setup["timestamp"],
            "direction": setup["direction"],
            "entry": setup["entry"],
            "sl": setup["sl"],
            "tp": setup["tp"],
            "atr": setup["atr"],
            "status": "OPEN",
            "bars_held": 0,
            "exit_time": None,
            "exit_price": None,
            "result": None,
            "r_multiple": None
        }
        
        self.current_position = trade
        self.position_bars_held = 0
        
        print(f"\n{'='*60}")
        print(f"  NEW PAPER TRADE #{trade['id']}")
        print(f"{'='*60}")
        print(f"  Direction: {trade['direction']}")
        print(f"  Entry: {trade['entry']}")
        print(f"  Stop Loss: {trade['sl']}")
        print(f"  Take Profit: {trade['tp']}")
        print(f"  ATR: {trade['atr']}")
        print(f"{'='*60}")
        
        return trade
    
    def check_position(self):
        """Check if current position hit SL/TP or should close."""
        if not self.current_position:
            return None
        
        if not mt5.initialize():
            return None
        
        # Get latest prices
        tick = mt5.symbol_info_tick(self.strategy["symbol"])
        if tick is None:
            mt5.shutdown()
            return None
        
        current_price = tick.bid if self.current_position["direction"] == "BUY" else tick.ask
        self.position_bars_held += 1
        
        # Check SL
        if self.current_position["direction"] == "BUY":
            if current_price <= self.current_position["sl"]:
                self.current_position["status"] = "CLOSED"
                self.current_position["exit_price"] = current_price
                self.current_position["result"] = "SL"
                self.current_position["r_multiple"] = -1
            elif current_price >= self.current_position["tp"]:
                self.current_position["status"] = "CLOSED"
                self.current_position["exit_price"] = current_price
                self.current_position["result"] = "TP"
                self.current_position["r_multiple"] = 2.5
        else:  # SELL
            if current_price >= self.current_position["sl"]:
                self.current_position["status"] = "CLOSED"
                self.current_position["exit_price"] = current_price
                self.current_position["result"] = "SL"
                self.current_position["r_multiple"] = -1
            elif current_price <= self.current_position["tp"]:
                self.current_position["status"] = "CLOSED"
                self.current_position["exit_price"] = current_price
                self.current_position["result"] = "TP"
                self.current_position["r_multiple"] = 2.5
        
        # Check max hold
        if self.position_bars_held >= self.strategy["max_hold_bars"]:
            self.current_position["status"] = "CLOSED"
            self.current_position["exit_price"] = current_price
            self.current_position["result"] = "TIMEOUT"
            
            if self.current_position["direction"] == "BUY":
                r = (current_price - self.current_position["entry"]) / (self.current_position["entry"] - self.current_position["sl"])
            else:
                r = (self.current_position["entry"] - current_price) / (self.current_position["sl"] - self.current_position["entry"])
            
            self.current_position["r_multiple"] = r
        
        self.current_position["bars_held"] = self.position_bars_held
        
        mt5.shutdown()
        
        # If closed, save and reset
        if self.current_position["status"] == "CLOSED":
            self.current_position["exit_time"] = datetime.now(timezone.utc).isoformat()
            self.trades.append(self.current_position)
            self.save_trade(self.current_position)
            
            print(f"\n  Position CLOSED:")
            print(f"    Result: {self.current_position['result']}")
            print(f"    R: {self.current_position['r_multiple']}")
            
            closed_trade = self.current_position
            self.current_position = None
            self.position_bars_held = 0
            return closed_trade
        
        return None
    
    def save_trade(self, trade):
        """Save trade to results file."""
        filepath = self.results_dir / "forward_trades.jsonl"
        with open(filepath, 'a') as f:
            f.write(json.dumps(trade, default=str) + '\n')
    
    def get_statistics(self):
        """Calculate current forward test statistics."""
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "expectancy": 0,
                "total_r": 0
            }
        
        r_values = [t["r_multiple"] for t in self.trades if t["r_multiple"] is not None]
        if not r_values:
            return {"total_trades": len(self.trades)}
        
        wins = sum(1 for r in r_values if r > 0)
        gross_profit = sum(r for r in r_values if r > 0)
        gross_loss = abs(sum(r for r in r_values if r < 0))
        
        return {
            "total_trades": len(r_values),
            "win_rate": wins / len(r_values),
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float('inf'),
            "expectancy": np.mean(r_values),
            "total_r": sum(r_values)
        }
    
    def run_once(self):
        """Run one cycle of the forward test."""
        # Check existing position
        if self.current_position:
            self.check_position()
        else:
            # Look for new setup
            setup = self.check_for_setup()
            if setup:
                self.execute_paper_trade(setup)
    
    def run_continuous(self, interval_minutes=15):
        """Run forward test continuously."""
        print("="*60)
        print("  FORWARD TESTING ENGINE - RUNNING")
        print("="*60)
        print(f"  Strategy: {self.strategy['name']}")
        print(f"  Symbol: {self.strategy['symbol']}")
        print(f"  Check interval: {interval_minutes} minutes")
        print(f"  Press Ctrl+C to stop")
        print("="*60)
        
        try:
            while True:
                self.run_once()
                
                # Print status every hour
                current_minute = datetime.now().minute
                if current_minute < interval_minutes:
                    stats = self.get_statistics()
                    if stats["total_trades"] > 0:
                        print(f"\n  Status Update:")
                        print(f"    Trades: {stats['total_trades']}")
                        print(f"    Win rate: {stats['win_rate']*100:.1f}%")
                        print(f"    PF: {stats['profit_factor']:.3f}")
                        print(f"    Expectancy: {stats['expectancy']:.3f}R")
                
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n\nForward test stopped.")
            stats = self.get_statistics()
            print(f"\nFinal Statistics:")
            print(f"  Trades: {stats['total_trades']}")
            if stats['total_trades'] > 0:
                print(f"  Win rate: {stats['win_rate']*100:.1f}%")
                print(f"  Profit factor: {stats['profit_factor']:.3f}")
                print(f"  Expectancy: {stats['expectancy']:.3f}R")
                print(f"  Total R: {stats['total_r']:.1f}")

if __name__ == "__main__":
    engine = ForwardTestEngine()
    
    # Run once for testing
    print("Testing forward test engine...")
    setup = engine.check_for_setup()
    if setup:
        print(f"Found setup: {setup['direction']} at {setup['entry']}")
    else:
        print("No setup found at this time (outside session or no FVG)")
    
    # For continuous running, uncomment:
    # engine.run_continuous(interval_minutes=15)
