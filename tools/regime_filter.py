"""REGIME FILTER - Only trade in favorable conditions."""
import MetaTrader5 as mt5
import pandas as pd

class RegimeFilter:
    """Ensures we only trade when regime is favorable."""
    
    def __init__(self):
        self.allowed_regimes = ["STRONG_UPTREND", "WEAK_UPTREND"]
        
    def check_regime(self):
        """Check current regime."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 200)
        mt5.shutdown()
        
        data = pd.DataFrame(rates)
        ema_50 = data['close'].ewm(span=50).mean().iloc[-1]
        ema_200 = data['close'].ewm(span=200).mean().iloc[-1]
        
        if ema_50 > ema_200 * 1.002:
            return "STRONG_UPTREND"
        elif ema_50 > ema_200:
            return "WEAK_UPTREND"
        elif ema_50 < ema_200 * 0.998:
            return "STRONG_DOWNTREND"
        else:
            return "WEAK_DOWNTREND"
    
    def can_trade(self):
        """Check if trading is allowed."""
        regime = self.check_regime()
        
        if regime is None:
            return False, "Cannot determine regime"
        
        if regime in self.allowed_regimes:
            return True, f"Favorable regime: {regime}"
        else:
            return False, f"Unfavorable regime: {regime}"
    
    def display_status(self):
        """Display current trading status."""
        can_trade, reason = self.can_trade()
        
        print("="*60)
        print("  REGIME FILTER STATUS")
        print("="*60)
        print(f"  Can trade: {'YES' if can_trade else 'NO'}")
        print(f"  Reason: {reason}")
        print(f"\n  Allowed regimes: {', '.join(self.allowed_regimes)}")
        print(f"  Current action: {'WAIT for uptrend' if not can_trade else 'READY to trade'}")
        print("="*60)
        
        return can_trade, reason

if __name__ == "__main__":
    filter = RegimeFilter()
    filter.display_status()
