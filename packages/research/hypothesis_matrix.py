"""SYSTEMATIC HYPOTHESIS TESTING - Research Matrix."""
import pandas as pd
import numpy as np
from itertools import product
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timezone
import json
from pathlib import Path

@dataclass
class HypothesisConfig:
    """Configuration for one hypothesis test."""
    name: str
    entry_type: str
    htf_timeframe: str
    exit_type: str
    rr_ratio: float
    session: str
    volatility_filter: str
    
class ResearchMatrix:
    """Tests multiple hypotheses systematically."""
    
    def __init__(self):
        self.results = []
        self.matrix_dir = Path("research/matrix_results")
        self.matrix_dir.mkdir(parents=True, exist_ok=True)
    
    def define_matrix(self) -> List[HypothesisConfig]:
        """Define the research matrix without testing everything."""
        
        # Select representative combinations (not exhaustive!)
        # This avoids overfitting by testing hypotheses, not parameters
        
        matrix = [
            # Pure FVG entries
            HypothesisConfig("FVG_H4_2R_London", "FVG", "H4", "RR", 2.0, "London", "None"),
            HypothesisConfig("FVG_H1_2R_London", "FVG", "H1", "RR", 2.0, "London", "None"),
            HypothesisConfig("FVG_H4H1_2R_London", "FVG", "H4+H1", "RR", 2.0, "London", "None"),
            
            # Pure OB entries
            HypothesisConfig("OB_H4_2R_London", "OB", "H4", "RR", 2.0, "London", "None"),
            HypothesisConfig("OB_H1_2R_London", "OB", "H1", "RR", 2.0, "London", "None"),
            HypothesisConfig("OB_H4H1_2R_London", "OB", "H4+H1", "RR", 2.0, "London", "None"),
            
            # Liquidity sweep combinations
            HypothesisConfig("SWEEP_MSS_H4_2R_London", "SWEEP+MSS", "H4", "RR", 2.0, "London", "None"),
            HypothesisConfig("SWEEP_FVG_H4_2R_London", "SWEEP+FVG", "H4", "RR", 2.0, "London", "None"),
            HypothesisConfig("SWEEP_MSS_FVG_H4_2R_London", "SWEEP+MSS+FVG", "H4", "RR", 2.0, "London", "None"),
            
            # Different R:R ratios
            HypothesisConfig("FVG_H4_15R_London", "FVG", "H4", "RR", 1.5, "London", "None"),
            HypothesisConfig("FVG_H4_25R_London", "FVG", "H4", "RR", 2.5, "London", "None"),
            
            # Different sessions
            HypothesisConfig("FVG_H4_2R_NY", "FVG", "H4", "RR", 2.0, "NY", "None"),
            HypothesisConfig("FVG_H4_2R_Overlap", "FVG", "H4", "RR", 2.0, "Overlap", "None"),
            
            # Volatility filters
            HypothesisConfig("FVG_H4_2R_London_ATR", "FVG", "H4", "RR", 2.0, "London", "ATR"),
            HypothesisConfig("FVG_H4_2R_London_LowVolExcl", "FVG", "H4", "RR", 2.0, "London", "LowVolExcl"),
        ]
        
        return matrix
    
    def test_hypothesis(self, config: HypothesisConfig, data: pd.DataFrame) -> Dict:
        """Test one hypothesis."""
        # Calculate indicators
        data = data.copy()
        
        # EMAs
        data['ema_20'] = data['close'].ewm(span=20).mean()
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean()
        
        # ATR
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        
        # Session filter
        data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
        if config.session == "London":
            session_mask = (data['hour'] >= 7) & (data['hour'] <= 11)
        elif config.session == "NY":
            session_mask = (data['hour'] >= 12) & (data['hour'] <= 16)
        elif config.session == "Overlap":
            session_mask = (data['hour'] >= 11) & (data['hour'] <= 13)
        else:
            session_mask = pd.Series(True, index=data.index)
        
        # Generate signals
        trades = []
        
        for i in range(200, len(data)):
            if not session_mask.iloc[i]:
                continue
            
            # Determine HTF bias
            if config.htf_timeframe == "H4":
                bias_bullish = data['ema_50'].iloc[i] > data['ema_200'].iloc[i]
            elif config.htf_timeframe == "H1":
                bias_bullish = data['ema_20'].iloc[i] > data['ema_50'].iloc[i]
            elif config.htf_timeframe == "H4+H1":
                bias_bullish = (data['ema_50'].iloc[i] > data['ema_200'].iloc[i] and 
                               data['ema_20'].iloc[i] > data['ema_50'].iloc[i])
            
            # Entry conditions based on type
            entry_signal = False
            direction = None
            
            if config.entry_type == "FVG":
                # FVG detection
                if i >= 2:
                    if bias_bullish and data['high'].iloc[i-2] < data['low'].iloc[i]:
                        entry_signal = True
                        direction = "BUY"
                    elif not bias_bullish and data['low'].iloc[i-2] > data['high'].iloc[i]:
                        entry_signal = True
                        direction = "SELL"
            
            elif config.entry_type == "OB":
                # Order Block detection (simplified)
                if i >= 5:
                    recent_low = data['low'].iloc[i-5:i].min()
                    recent_high = data['high'].iloc[i-5:i].max()
                    if bias_bullish and data['low'].iloc[i] <= recent_low * 1.001:
                        entry_signal = True
                        direction = "BUY"
                    elif not bias_bullish and data['high'].iloc[i] >= recent_high * 0.999:
                        entry_signal = True
                        direction = "SELL"
            
            elif config.entry_type == "SWEEP+MSS":
                # Liquidity sweep + MSS
                if i >= 10:
                    lookback = data.iloc[i-10:i]
                    if bias_bullish and data['low'].iloc[i] < lookback['low'].min():
                        if data['close'].iloc[i] > lookback['high'].max():
                            entry_signal = True
                            direction = "BUY"
                    elif not bias_bullish and data['high'].iloc[i] > lookback['high'].max():
                        if data['close'].iloc[i] < lookback['low'].min():
                            entry_signal = True
                            direction = "SELL"
            
            if entry_signal and direction:
                entry = data['close'].iloc[i]
                atr = data['atr'].iloc[i]
                
                if direction == "BUY":
                    sl = entry - (atr * 1.5)
                    tp = entry + (atr * 1.5 * config.rr_ratio)
                else:
                    sl = entry + (atr * 1.5)
                    tp = entry - (atr * 1.5 * config.rr_ratio)
                
                # Simulate trade
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if direction == "BUY":
                        if data['low'].iloc[j] <= sl:
                            trades.append({"r": -1})
                            break
                        elif data['high'].iloc[j] >= tp:
                            trades.append({"r": config.rr_ratio})
                            break
                    else:
                        if data['high'].iloc[j] >= sl:
                            trades.append({"r": -1})
                            break
                        elif data['low'].iloc[j] <= tp:
                            trades.append({"r": config.rr_ratio})
                            break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    if direction == "BUY":
                        r = (exit_price - entry) / (entry - sl)
                    else:
                        r = (entry - exit_price) / (sl - entry)
                    trades.append({"r": r})
        
        # Calculate statistics
        if trades:
            trades_df = pd.DataFrame(trades)
            wins = (trades_df['r'] > 0).sum()
            total = len(trades_df)
            gross_profit = trades_df[trades_df['r'] > 0]['r'].sum()
            gross_loss = abs(trades_df[trades_df['r'] < 0]['r'].sum())
            
            return {
                "hypothesis": config.name,
                "trades": total,
                "win_rate": wins / total if total > 0 else 0,
                "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float('inf'),
                "expectancy": trades_df['r'].mean() if total > 0 else 0,
                "total_r": trades_df['r'].sum() if total > 0 else 0
            }
        
        return {"hypothesis": config.name, "trades": 0}
    
    def run_matrix(self, data: pd.DataFrame):
        """Run all hypotheses in matrix."""
        print("="*60)
        print("  RESEARCH MATRIX - SYSTEMATIC HYPOTHESIS TESTING")
        print("="*60)
        
        matrix = self.define_matrix()
        print(f"\nTesting {len(matrix)} hypotheses...")
        
        for config in matrix:
            result = self.test_hypothesis(config, data)
            self.results.append(result)
            
            # Print progress
            if result["trades"] > 0:
                print(f"\n{config.name}:")
                print(f"  Trades: {result['trades']}")
                print(f"  Win rate: {result['win_rate']*100:.1f}%")
                print(f"  PF: {result['profit_factor']:.3f}")
                print(f"  Expectancy: {result['expectancy']:.3f}R")
            else:
                print(f"\n{config.name}: No trades")
        
        # Rank results
        valid_results = [r for r in self.results if r["trades"] >= 20]
        valid_results.sort(key=lambda x: x["expectancy"], reverse=True)
        
        print(f"\n{'='*60}")
        print("  TOP HYPOTHESES (min 20 trades)")
        print("="*60)
        for i, result in enumerate(valid_results[:10], 1):
            print(f"\n{i}. {result['hypothesis']}")
            print(f"   Trades: {result['trades']}")
            print(f"   Win rate: {result['win_rate']*100:.1f}%")
            print(f"   PF: {result['profit_factor']:.3f}")
            print(f"   Expectancy: {result['expectancy']:.3f}R")
        
        # Save results
        self.save_results()
        
        return valid_results
    
    def save_results(self):
        """Save matrix results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.matrix_dir / f"matrix_results_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to {filepath}")

if __name__ == "__main__":
    # Test with real data
    import MetaTrader5 as mt5
    
    if mt5.initialize():
        rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 10000)
        if rates is not None:
            data = pd.DataFrame(rates)
            data['timestamp'] = pd.to_datetime(data['time'], unit='s')
            
            matrix = ResearchMatrix()
            results = matrix.run_matrix(data)
        
        mt5.shutdown()
