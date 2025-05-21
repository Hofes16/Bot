import telegram
import logging
import os
from dotenv import load_dotenv

class TelegramNotifier:
    def __init__(self, log_file):
        load_dotenv()
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID çevresel değişkeni eksik")
        self.bot = telegram.Bot(token=self.bot_token)
        self.logger = logging.getLogger('BotLogger')
        self.log_file = log_file

    def send_message(self, message):
        try:
            self.bot.send_message(chat_id=self.chat_id, text=message)
            self.logger.info(f"Telegram mesajı gönderildi: {message}")
        except Exception as e:
            self.logger.error(f"[telegram_notifier.py:TelegramNotifier.send_message] Telegram mesajı gönderilemedi: {e}")