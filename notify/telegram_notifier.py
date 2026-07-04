"""
Telegram notification module for Forex AI Trading System.
"""

import time
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    def send_photo(self, photo_path, caption=None):
        """Send a photo to the configured Telegram chat."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not set. Skipping photo.")
            return False
        
        url = f"{self.base_url}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {'chat_id': self.chat_id}
                if caption:
                    data['caption'] = caption
                response = requests.post(url, data=data, files=files, timeout=30)
            if response.status_code != 200:
                logger.error(f"Telegram photo send failed: {response.text}")
                return False
            return True
        except Exception as e:
            logger.error(f"Telegram photo error: {e}")
            return False
        
    def send_message(self, text, parse_mode='HTML'):
        """Send a message to the configured Telegram chat with retry logic."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not set. Skipping notification.")
            return False
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        for attempt in range(3):
            try:
                response = requests.post(url, data=payload, timeout=15)
                if response.status_code == 200:
                    return True
                logger.error(f"Telegram send failed: {response.text}")
            except Exception as e:
                logger.error(f"Telegram error (attempt {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(5)
        return False

    def format_trade_entry(self, signal, lot_size, balance):
        """Format a trade entry notification."""
        emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"
        return (
            f"{emoji} <b>NEW TRADE OPENED</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>{signal['pair']}</b>  {signal['signal']}\n"
            f"🎯 Entry: <code>{signal['entry']:.5f}</code>\n"
            f"🛑 Stop Loss: <code>{signal['stop_loss']:.5f}</code>\n"
            f"✅ Take Profit: <code>{signal['take_profit']:.5f}</code>\n"
            f"📈 Confidence: {signal['confidence']:.0%} ({signal['strength']})\n"
            f"💰 Lot Size: {lot_size}\n"
            f"💵 Balance: ${balance:,.2f}\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def format_trade_exit(self, pair, pnl, balance, reason="Closed"):
        """Format a trade exit notification."""
        emoji = "💰" if pnl > 0 else "📉"
        return (
            f"{emoji} <b>TRADE CLOSED</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>{pair}</b>\n"
            f"💵 P&L: <b>${pnl:+.2f}</b>\n"
            f"🏦 New Balance: ${balance:,.2f}\n"
            f"📋 Reason: {reason}\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def format_error(self, error_message):
        """Format an error notification."""
        return (
            f"🚨 <b>ERROR ALERT</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"❌ {error_message}\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def format_daily_summary(self, trades_count, pnl, win_rate):
        """Format end-of-day summary."""
        return (
            f"📅 <b>DAILY SUMMARY</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔢 Trades: {trades_count}\n"
            f"💵 Daily P&L: ${pnl:+.2f}\n"
            f"📊 Win Rate: {win_rate:.1f}%\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )