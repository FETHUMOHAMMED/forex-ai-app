# paper_trade.py – professional live trading engine
import time
import logging
from datetime import datetime, timezone
import MetaTrader5 as mt5
from real_ai_service import RealAITrader, close_expired_trades

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Cooldown for “market closed” messages (per symbol)
# ------------------------------------------------------------------
LAST_MARKET_CLOSED_LOG = {}

def should_log_market_closed(symbol):
    """Only log 'market closed' for the same symbol once every 30 minutes."""
    now = datetime.now(timezone.utc)
    last = LAST_MARKET_CLOSED_LOG.get(symbol)
    if last is None or (now - last).total_seconds() > 1800:
        LAST_MARKET_CLOSED_LOG[symbol] = now
        return True
    return False

# ------------------------------------------------------------------
# Global forex market‑open check (using EURUSDm/EURUSD tick freshness)
# ------------------------------------------------------------------
def forex_market_is_open():
    if not mt5.initialize():
        return False
    for sym in ['EURUSDm', 'EURUSD']:
        tick = mt5.symbol_info_tick(sym)
        if tick is None:
            continue
        tick_time = datetime.fromtimestamp(tick.time, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        if (now - tick_time).total_seconds() < 300:
            return True
        else:
            return False   # stale tick → closed
    return False

# ------------------------------------------------------------------
# Main paper‑trading loop
# ------------------------------------------------------------------
def run_paper_trading():
    trader = RealAITrader()

    while True:
        now = datetime.now(timezone.utc)

        # ---- 0. Weekend / late Friday – deep sleep, no scanning ----
        if now.weekday() == 5:                      # Saturday
            logger.info("Weekend – sleeping 1 hour")
            time.sleep(3600)
            continue
        if now.weekday() == 6 and now.hour < 21:    # Sunday before 21 UTC (rough market open)
            logger.info("Sunday, waiting for market open – sleeping 30 min")
            time.sleep(1800)
            continue
        if now.weekday() == 4 and now.hour >= 18:   # Friday after 18 UTC
            logger.info("Friday evening – no new entries, sleeping 1 hour")
            time.sleep(3600)
            continue

        # ---- 1. Global market‑open check ----
        if not forex_market_is_open():
            # Log only once per 30 min to avoid spam
            if should_log_market_closed('global'):
                logger.info("🌙 Forex market appears closed")
            time.sleep(300)   # wait 5 min before next check
            continue

        # ---- 2. Time‑based exit (cooldown & per‑symbol checks inside) ----
        try:
            close_expired_trades(max_hours=12, cooldown_minutes=15)
        except Exception as e:
            logger.error(f"Time‑exit error: {e}")

        # ---- 3. Scan for new signals ----
        for pair in trader.pairs:
            try:
                signal = trader.get_real_signal(pair)   # already filters trending + regime
                if signal is None:
                    continue
                logger.info(f"✅ PAPER TRADE SIGNAL: {signal['signal']} {pair} @ {signal['entry']:.5f} "
                            f"SL={signal['stop_loss']:.5f} TP={signal['take_profit']:.5f}")
                # ---- Uncomment when ready to place real orders ----
                # place_order(signal)
            except Exception as e:
                logger.error(f"Error processing {pair}: {e}")

        # ---- 4. Wait 15 minutes before next cycle ----
        time.sleep(900)

if __name__ == "__main__":
    run_paper_trading()