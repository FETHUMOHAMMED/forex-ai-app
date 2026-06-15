"""
Slack notification module for Forex AI Trading System.
"""

import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SlackNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_message(self, text):
        """Send a message to the Slack channel via incoming webhook."""
        if not self.webhook_url:
            logger.warning("Slack webhook URL not set. Skipping notification.")
            return False

        payload = {
            "text": text,
            "mrkdwn": True
        }
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"Slack send failed: {response.text}")
                return False
            return True
        except Exception as e:
            logger.error(f"Slack error: {e}")
            return False

    # The following methods format messages exactly like Telegram,
    # but we can keep the same HTML‑like formatting because Slack uses mrkdwn.
    def format_trade_entry(self, signal, lot_size, balance):
        emoji = ":large_green_circle:" if signal['signal'] == 'BUY' else ":red_circle:"
        return (
            f"{emoji} *NEW TRADE OPENED*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 *{signal['pair']}*  {signal['signal']}\n"
            f"🎯 Entry: `{signal['entry']:.5f}`\n"
            f"🛑 Stop Loss: `{signal['stop_loss']:.5f}`\n"
            f"✅ Take Profit: `{signal['take_profit']:.5f}`\n"
            f"📈 Confidence: {signal['confidence']:.0%} ({signal['strength']})\n"
            f"💰 Lot Size: {lot_size}\n"
            f"💵 Balance: ${balance:,.2f}\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def format_trade_exit(self, pair, pnl, balance, reason="Closed"):
        emoji = ":moneybag:" if pnl > 0 else ":chart_with_downwards_trend:"
        return (
            f"{emoji} *TRADE CLOSED*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 *{pair}*\n"
            f"💵 P&L: *${pnl:+.2f}*\n"
            f"🏦 New Balance: ${balance:,.2f}\n"
            f"📋 Reason: {reason}\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def format_error(self, error_message):
        return (
            f":rotating_light: *ERROR ALERT*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"❌ {error_message}\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def format_daily_summary(self, trades_count, pnl, win_rate):
        return (
            f":calendar: *DAILY SUMMARY*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔢 Trades: {trades_count}\n"
            f"💵 Daily P&L: ${pnl:+.2f}\n"
            f"📊 Win Rate: {win_rate:.1f}%\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )