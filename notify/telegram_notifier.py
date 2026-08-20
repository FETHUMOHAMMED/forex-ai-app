"""
Telegram notification module for Forex AI Trading System.
Institutional-grade notifications with full AI metadata.
"""
import time, requests, logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, message):
        if not self.bot_token or not self.chat_id:
            return False
        url = f"{self.base_url}/sendMessage"
        for attempt in range(3):
            try:
                response = requests.post(url, json={
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }, timeout=30)
                if response.status_code == 200:
                    return True
                logger.error(f"Telegram send failed: {response.text}")
            except Exception as e:
                logger.error(f"Telegram error (attempt {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(5)
        return False

    def format_trade_entry(self, signal, lot_size, balance, account=''):
        emoji = "??" if signal['signal'] == 'BUY' else "??"
        confidence = signal.get('confidence', 0)
        regime = signal.get('institutional_bias', 'N/A')
        dealer = signal.get('dealer_pressure', 'N/A')
        liquidity = signal.get('liquidity_state', 'N/A')
        inst_score = signal.get('institutional_score', 'N/A')
        ticket = signal.get('ticket', '')
        
        msg = f"{emoji} <b>NEW TRADE OPENED</b>\n"
        msg += f"??????????????????\n"
        msg += f"?? <b>{signal['pair']}</b>  {signal['signal']}\n"
        if account:
            msg += f"?? Account: {account}\n"
        if ticket:
            msg += f"?? Ticket: {ticket}\n"
        msg += f"?? Entry: <code>{signal['entry']:.5f}</code>\n"
        msg += f"?? Stop Loss: <code>{signal['stop_loss']:.5f}</code>\n"
        msg += f"? Take Profit: <code>{signal['take_profit']:.5f}</code>\n"
        msg += f"\n?? <b>AI ANALYSIS</b>\n"
        msg += f"?? Confidence: {confidence:.0%}\n"
        if regime != 'N/A':
            msg += f"?? Regime: {regime}\n"
        if dealer != 'N/A':
            msg += f"?? Dealer: {dealer}\n"
        if liquidity != 'N/A':
            msg += f"?? Liquidity: {liquidity}\n"
        if inst_score != 'N/A':
            msg += f"?? Inst Score: {inst_score:.0f}/100\n"
        msg += f"\n?? Lot Size: {lot_size}\n"
        msg += f"?? Balance: ${balance:,.2f}\n"
        msg += f"?? {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return msg

    def format_trade_exit(self, pair, pnl, balance, reason="Closed"):
        emoji = "??" if pnl > 0 else "??" if pnl < 0 else "??"
        result = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
        msg = f"{emoji} <b>TRADE CLOSED</b>\n"
        msg += f"??????????????????\n"
        msg += f"?? <b>{pair}</b>\n"
        msg += f"?? Result: {result}\n"
        msg += f"?? P&L: <b>${pnl:+.2f}</b>\n"
        msg += f"?? Reason: {reason}\n"
        msg += f"?? New Balance: ${balance:,.2f}\n"
        msg += f"?? {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return msg

    def format_error(self, error_message):
        return (
            f"?? <b>ERROR ALERT</b>\n"
            f"??????????????????\n"
            f"? {error_message}\n"
            f"?? {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
