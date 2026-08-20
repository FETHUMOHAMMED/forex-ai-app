"""ENHANCED FORWARD TEST - Monitor regime changes."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import json
from pathlib import Path

class EnhancedForwardTest:
    """Forward test with regime monitoring."""
    
    def __init__(self):
        self.results_dir = Path("research/forward_test/enhanced")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def check_trend_regime(self):
        """Check current USDJPY trend regime."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 200)
        mt5.shutdown()
        
        data = pd.DataFrame(rates)
        ema_50 = data['close'].ewm(span=50).mean().iloc[-1]
        ema_200 = data['close'].ewm(span=200).mean().iloc[-1]
        
        if ema_50 > ema_200 * 1.002:
            regime = "STRONG_UPTREND"
        elif ema_50 > ema_200:
            regime = "WEAK_UPTREND"
        elif ema_50 < ema_200 * 0.998:
            regime = "STRONG_DOWNTREND"
        else:
            regime = "WEAK_DOWNTREND"
        
        return {
            "regime": regime,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def should_trade_in_regime(self, regime):
        """Determine if we should trade in current regime."""
        # Long-only strategy - only trade in uptrends
        if "UPTREND" in regime:
            return True, f"Favorable regime: {regime}"
        else:
            return False, f"Unfavorable regime: {regime} (long-only strategy)"
    
    def run_check(self):
        """Run one forward test check."""
        regime_info = self.check_trend_regime()
        
        if regime_info:
            should_trade, reason = self.should_trade_in_regime(regime_info["regime"])
            
            result = {
                **regime_info,
                "should_trade": should_trade,
                "reason": reason
            }
            
            # Save regime check
            filepath = self.results_dir / "regime_checks.jsonl"
            with open(filepath, 'a') as f:
                f.write(json.dumps(result) + '\n')
            
            return result
        
        return None

if __name__ == "__main__":
    tester = EnhancedForwardTest()
    result = tester.run_check()
    
    if result:
        print("="*60)
        print("  ENHANCED FORWARD TEST CHECK")
        print("="*60)
        print(f"  Regime: {result['regime']}")
        print(f"  Should trade: {result['should_trade']}")
        print(f"  Reason: {result['reason']}")
        print("="*60)
