import pandas as pd
import ta
from datetime import datetime
import logging
import logging.handlers
from colorama import Fore, Style, init
from gate_api import ApiClient, Configuration, FuturesApi, FuturesOrder
import threading
import pygame
import time
import requests
from dotenv import load_dotenv
import os
import hmac
import hashlib

init(autoreset=True)
load_dotenv()

class CustomConfiguration(Configuration):
    def __init__(self, key, secret):
        super().__init__(key=key, secret=secret)
        self.api_key = key
        self.api_secret = secret.encode('utf-8')

    def sign(self, method, url, query_string=None, payload_string=None):
        t = str(int(time.time()))
        m = hashlib.sha512()
        m.update((payload_string or '').encode('utf-8'))
        hashed_payload = m.hexdigest()
        s = f'{method}\n{url}\n{query_string or ""}\n{hashed_payload}\n{t}'
        sign = hmac.new(self.api_secret, s.encode('utf-8'), hashlib.sha512).hexdigest()
        return {'KEY': self.api_key, 'Timestamp': t, 'SIGN': sign}

class BotLogic:
    def __init__(self):
        self.bot_running = False
        self.symbol = "DOGE_USDT"
        self.found_symbol = None
        self.exchange = None
        self.balance = 0
        self.last_price = 0
        self.last_rsi = 0
        self.last_ma7_distance = 0
        self.last_trade_profit = 0
        self.btc_price = 0
        self.eth_price = 0
        self.long_basarili = 0
        self.long_basarisiz = 0
        self.short_basarili = 0
        self.short_basarisiz = 0
        self.data_source = "gateio"
        self.mum_sonu_bekle = False
        self.current_long_position = None
        self.current_short_position = None
        self.position_entry_price = 0
        self.position_profit = 0
        self.monitor_thread_long = None
        self.monitor_thread_short = None
        self.disable_position = "Hiçbiri"
        self.last_coin_list_log = None

        self.long_settings = {
            'symbol': 'DOGE_USDT',
            'tp_percent': 0.01,
            'sl_percent': 0.017,
            'leverage': 15,
            'rsi_threshold': 20.0,
            'rsi_condition': 'Küçüktür',
            'ma7_threshold': 0.007,
            'bollinger_band_break_pct': 0.0025,
            'volatility_threshold': 0.5,
            'allowed_hours': list(range(24))
        }
        self.short_settings = {
            'symbol': 'DOGE_USDT',
            'tp_percent': 0.01,
            'sl_percent': 0.017,
            'leverage': 15,
            'rsi_threshold': 80.0,
            'rsi_condition': 'Büyüktür',
            'ma7_threshold': 0.007,
            'bollinger_band_break_pct': 0.0025,
            'volatility_threshold': 0.5,
            'allowed_hours': list(range(24))
        }

        self.gate_api_key = os.getenv("GATE_API_KEY")
        self.gate_api_secret = os.getenv("GATE_API_SECRET")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

        self.log_file = "islem_log.txt"
        self.coin_list_log_file = "coin_list_log.txt"

        self.setup_logging()
        self.setup_exchange()
        self.fetch_initial_data()
        pygame.mixer.init()

    def setup_logging(self):
        self.logger = logging.getLogger('BotLogger')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.handlers.TimedRotatingFileHandler(
            self.log_file, when='H', interval=2, backupCount=100, encoding='utf-8'
        )
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        coin_list_logger = logging.getLogger('CoinListLogger')
        coin_list_logger.setLevel(logging.INFO)
        coin_handler = logging.FileHandler(self.coin_list_log_file, encoding='utf-8')
        coin_handler.setFormatter(formatter)
        coin_list_logger.addHandler(coin_handler)

    def send_telegram_message(self, message):
        try:
            if not self.telegram_bot_token or not self.telegram_chat_id:
                raise ValueError("TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID eksik")
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message
            }
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                raise Exception(f"Telegram API hatası: {response.text}")
            self.logger.info(f"Telegram mesajı gönderildi: {message}")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.send_telegram_message] Telegram mesajı gönderilemedi: {e}")
            print(f"Telegram mesajı gönderilemedi: {e}")

    def setup_exchange(self):
        try:
            config = CustomConfiguration(key=self.gate_api_key, secret=self.gate_api_secret)
            self.exchange = FuturesApi(ApiClient(config))
            self.balance = self.get_balance()
            self.logger.info("Borsa bağlantısı başarılı")
            self.send_telegram_message("Bot başlatıldı! Borsa bağlantısı başarılı.")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.setup_exchange] Borsa bağlantı hatası: {e}")
            self.send_telegram_message(f"Hata: Borsa bağlantısı kurulamadı: {e}")

    def fetch_initial_data(self):
        try:
            self.get_coin_list()
            self.update_data()
            self.logger.info("Başlangıç verileri başarıyla çekildi")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.fetch_initial_data] Başlangıç verileri çekilemedi: {e}")
            self.send_telegram_message(f"Hata: Başlangıç verileri çekilemedi: {e}")

    def get_balance(self):
        try:
            settle = "usdt"
            futures_account = self.exchange.list_futures_accounts(settle)
            balance = float(futures_account.available)
            self.logger.info(f"Kullanılabilir bakiye: {balance:.2f} USDT")
            self.send_telegram_message(f"Toplam Bakiye: {balance:.2f} USDT")
            return balance
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.get_balance] Bakiye alınamadı: {e}")
            self.send_telegram_message(f"Hata: Bakiye alınamadı: {e}")
            return 0

    def get_coin_list(self):
        try:
            settle = "usdt"
            contracts = self.exchange.list_futures_contracts(settle)
            coin_list = [contract.name for contract in contracts]
            today = datetime.now().date()
            if self.last_coin_list_log != today:
                coin_list_logger = logging.getLogger('CoinListLogger')
                coin_list_logger.info(f"Coin listesi: {coin_list}")
                self.last_coin_list_log = today
            return sorted(coin_list)
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.get_coin_list] Coin listesi alınamadı: {e}")
            self.send_telegram_message(f"Hata: Coin listesi alınamadı: {e}")
            return []

    def save_selected_coins(self, long_coin, short_coin):
        try:
            self.logger.info(f"Seçilen Coin: Long={long_coin}, Short={short_coin}")
            self.send_telegram_message(f"Seçilen Coin: Long={long_coin}, Short={short_coin}")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.save_selected_coins] Coin seçimleri loglanamadı: {e}")
            self.send_telegram_message(f"Hata: Coin seçimleri loglanamadı: {e}")

    def play_sound(self, sound_path):
        try:
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.play_sound] Ses çalınamadı: {e}")
            self.send_telegram_message(f"Hata: Ses çalınamadı: {e}")

    def check_symbol_exists(self, symbol):
        if self.found_symbol:
            return True
        try:
            settle = "usdt"
            contracts = self.exchange.list_futures_contracts(settle)
            for contract in contracts:
                if contract.name == symbol:
                    self.found_symbol = contract.name
                    self.symbol = self.found_symbol
                    self.logger.info(f"Sembol bulundu: {self.found_symbol}")
                    return True
            self.logger.error(f"{symbol} sembolü Gate.io vadeli işlemde bulunamadı")
            self.send_telegram_message(f"Hata: {symbol} sembolü Gate.io vadeli işlemde bulunamadı")
            return False
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.check_symbol_exists] Sembol kontrol hatası: {e}")
            self.send_telegram_message(f"Hata: Sembol kontrol hatası: {e}")
            return False

    def fetch_ohlcv(self, symbol, timeframe='15m', limit=100):
        try:
            settle = "usdt"
            candlesticks = self.exchange.list_futures_candlesticks(settle, symbol, interval=timeframe, limit=limit)
            if not candlesticks:
                self.logger.error(f"OHLCV verisi boş döndü. Sembol: {symbol}, Zaman Aralığı: {timeframe}, Limit: {limit}")
                self.send_telegram_message(f"Hata: OHLCV verisi boş döndü. Sembol: {symbol}")
                return None
            data = [[int(c.t), float(c.o), float(c.h), float(c.l), float(c.c), float(c.v)] for c in candlesticks]
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            return df
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.fetch_ohlcv] OHLCV verisi alınamadı: {e}. Sembol: {symbol}, Zaman Aralığı: {timeframe}, Limit: {limit}")
            self.send_telegram_message(f"Hata: OHLCV verisi alınamadı: {e}")
            return None

    def calculate_indicators(self, df):
        try:
            if len(df) < 7:
                self.logger.error("Yetersiz veri: En az 7 mum gerekli")
                self.send_telegram_message("Hata: Yetersiz veri, en az 7 mum gerekli")
                return None
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=6).rsi()
            df['ma7'] = df['close'].rolling(window=7).mean()
            df['ma7_distance'] = (df['close'] - df['ma7']) / df['ma7']
            bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            df['bollinger_hband'] = bollinger.bollinger_hband()
            df['bollinger_lband'] = bollinger.bollinger_lband()
            df['volatility'] = df['close'].pct_change().rolling(window=20).std() * 100
            return df
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.calculate_indicators] Indikatör hesaplama hatası: {e}")
            self.send_telegram_message(f"Hata: Indikatör hesaplama hatası: {e}")
            return None

    def update_data(self):
        if not self.check_symbol_exists(self.symbol):
            self.logger.error(f"Veri güncellenemedi: {self.symbol} sembolü bulunamadı")
            return
        try:
            settle = "usdt"
            btc_candles = self.exchange.list_futures_candlesticks(settle, "BTC_USDT", interval="15m", limit=1)
            if btc_candles:
                self.btc_price = float(btc_candles[0].c)
            eth_candles = self.exchange.list_futures_candlesticks(settle, "ETH_USDT", interval="15m", limit=1)
            if eth_candles:
                self.eth_price = float(eth_candles[0].c)
            self.balance = self.get_balance()
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.update_data] BTC/ETH fiyatları veya bakiye alınamadı: {e}")
            self.send_telegram_message(f"Hata: BTC/ETH fiyatları veya bakiye alınamadı: {e}")

        df = self.fetch_ohlcv(self.symbol)
        if df is None:
            self.logger.error("Veri alınamadı, güncelleme yapılmadı")
            return
        df = self.calculate_indicators(df)
        if df is None:
            self.logger.error("Indikatörler hesaplanamadı, güncelleme yapılmadı")
            return
        self.last_price = df['close'].iloc[-1]
        self.last_rsi = df['rsi'].iloc[-1]
        self.last_ma7_distance = df['ma7_distance'].iloc[-1] * 100
        self.logger.info(f"Veriler güncellendi: {self.symbol}, Fiyat: {self.last_price:.4f}, RSI: {self.last_rsi:.2f}, MA7 Uzaklık: {self.last_ma7_distance:.2f}%")

    def trade_logic(self):
        if not self.bot_running:
            return
        self.update_data()
        current_hour = datetime.now().hour
        if self.disable_position != "Long" and not self.current_long_position and current_hour in self.long_settings['allowed_hours']:
            settings = self.long_settings
            if (self.last_rsi < settings['rsi_threshold'] if settings['rsi_condition'] == 'Küçüktür' else self.last_rsi > settings['rsi_threshold']) and \
               self.last_ma7_distance < -settings['ma7_threshold'] * 100:
                self.open_position('LONG')
        if self.disable_position != "Short" and not self.current_short_position and current_hour in self.short_settings['allowed_hours']:
            settings = self.short_settings
            if (self.last_rsi > settings['rsi_threshold'] if settings['rsi_condition'] == 'Büyüktür' else self.last_rsi < settings['rsi_threshold']) and \
               self.last_ma7_distance > settings['ma7_threshold'] * 100:
                self.open_position('SHORT')

    def open_position(self, position_type):
        try:
            settle = "usdt"
            settings = self.long_settings if position_type == 'LONG' else self.short_settings
            self.exchange.update_position_leverage(settle, self.symbol, str(settings['leverage']))
            self.balance = self.get_balance()
            if self.balance < 5:
                self.logger.warning("Bakiye yetersiz, işlem açılamadı. Minimum 5 USDT gerekli")
                self.send_telegram_message("Hata: Bakiye yetersiz, minimum 5 USDT gerekli")
                return False

            leverage = settings['leverage']
            position_value = self.balance * 0.9 * leverage
            order_size = int(position_value / self.last_price)
            order_size = order_size if position_type == 'LONG' else -order_size

            order = FuturesOrder(contract=self.symbol, size=order_size, price="0", tif='ioc')
            order_response = self.exchange.create_futures_order(settle, order)
            self.logger.info(f"{position_type} pozisyon emri: ID {order_response.id}, Durum: {order_response.status}, Miktar: {order_response.size}, Kalan: {order_response.left}")
            if order_response.status == 'finished' and order_response.left == 0:
                self.logger.info(f"{position_type} pozisyon başarıyla açıldı")
                self.play_sound("islemegirdi.wav")
                self.send_telegram_message(
                    f"{position_type} pozisyon açıldı!\nSembol: {self.symbol}\nFiyat: {self.last_price:.4f}\nKaldıraç: {leverage}x\nBakiye: {self.balance:.2f} USDT\nPozisyon Değeri: {position_value:.2f} USDT"
                )
            else:
                self.logger.warning(f"{position_type} pozisyon açılamadı, Durum: {order_response.status}, Kalan: {order_response.left}")
                self.send_telegram_message(f"Hata: {position_type} pozisyon açılamadı, Durum: {order_response.status}")
                return False

            tp_price = self.last_price * (1 + settings['tp_percent']) if position_type == 'LONG' else self.last_price * (1 - settings['tp_percent'])
            sl_price = self.last_price * (1 - settings['sl_percent']) if position_type == 'LONG' else self.last_price * (1 + settings['sl_percent'])
            self.logger.info(f"{position_type} pozisyon açıldı. Fiyat: {self.last_price}, TP: {tp_price}, SL: {sl_price}, Kaldıraç: {leverage}x")
            if position_type == 'LONG':
                self.current_long_position = {'entry_price': self.last_price, 'size': order_size}
            else:
                self.current_short_position = {'entry_price': self.last_price, 'size': order_size}
            self.position_entry_price = self.last_price
            monitor_thread = threading.Thread(target=self.monitor_position, args=(position_type, tp_price, sl_price, order_size))
            if position_type == 'LONG':
                self.monitor_thread_long = monitor_thread
            else:
                self.monitor_thread_short = monitor_thread
            monitor_thread.start()
            return {'tp_price': tp_price, 'sl_price': sl_price, 'order_size': order_size}
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.open_position] {position_type} pozisyon açılamadı: {e}")
            self.send_telegram_message(f"Hata: {position_type} pozisyon açılamadı: {e}")
            return False

    def close_position(self, position_type, order_size):
        settle = "usdt"
        try:
            close_size = -order_size if position_type == 'LONG' else abs(order_size)
            order = FuturesOrder(contract=self.symbol, size=close_size, price="0", tif='ioc')
            response = self.exchange.create_futures_order(settle, order)
            self.logger.info(f"{position_type} pozisyon kapatma emri: ID {response.id}, Durum: {response.status}, Miktar: {response.size}")
            position = self.exchange.get_position(settle, self.symbol)
            if position.size == 0:
                self.logger.info(f"{position_type} pozisyon tamamen kapatıldı")
                self.send_telegram_message(f"{position_type} pozisyon kapatıldı!\nSembol: {self.symbol}\nBakiye: {self.balance:.2f} USDT")
            else:
                self.logger.warning(f"{position_type} pozisyon hala açık: Kalan miktar {position.size}")
                self.send_telegram_message(f"Uyarı: {position_type} pozisyon hala açık, kalan miktar: {position.size}")
            return response
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.close_position] {position_type} pozisyon kapatılamadı: {e}")
            self.send_telegram_message(f"Hata: {position_type} pozisyon kapatılamadı: {e}")
            return False

    def monitor_position(self, position_type, tp_price, sl_price, order_size):
        settle = "usdt"
        current_position_attr = 'current_long_position' if position_type == 'LONG' else 'current_short_position'
        settings = self.long_settings if position_type == 'LONG' else self.short_settings
        while self.bot_running and getattr(self, current_position_attr):
            df = self.fetch_ohlcv(self.symbol)
            if df is None:
                time.sleep(3)
                continue
            current_price = df['close'].iloc[-1]
            leverage = settings['leverage']
            if position_type == 'LONG':
                self.position_profit = (current_price - self.position_entry_price) * order_size * leverage
            else:
                self.position_profit = (self.position_entry_price - current_price) * abs(order_size) * leverage

            if position_type == 'LONG':
                if current_price >= tp_price:
                    profit = self.balance * settings['tp_percent'] * (leverage / 15)
                    self.long_basarili += 1
                    self.logger.info(f"LONG pozisyon kapatıldı. Sebep: TP, Kar/Zarar: {profit:.2f} USDT, Yeni Bakiye: {self.balance + profit:.2f} USDT")
                    self.position_profit = profit
                    self.last_trade_profit += profit
                    self.balance += profit
                    self.close_position(position_type, order_size)
                    self.play_sound("islemkapandi.wav")
                    self.send_telegram_message(
                        f"LONG pozisyon kapatıldı!\nSebep: Take Profit\nKar/Zarar: {profit:.2f} USDT\nYeni Bakiye: {self.balance:.2f} USDT"
                    )
                    self.current_long_position = None
                    break
                elif current_price <= sl_price:
                    loss = -self.balance * settings['sl_percent'] * (leverage / 15)
                    self.long_basarisiz += 1
                    self.logger.info(f"LONG pozisyon kapatıldı. Sebep: SL, Kar/Zarar: {loss:.2f} USDT, Yeni Bakiye: {self.balance + loss:.2f} USDT")
                    self.position_profit = loss
                    self.last_trade_profit += loss
                    self.balance += loss
                    self.close_position(position_type, order_size)
                    self.play_sound("islemkapandi.wav")
                    self.send_telegram_message(
                        f"LONG pozisyon kapatıldı!\nSebep: Stop Loss\nKar/Zarar: {loss:.2f} USDT\nYeni Bakiye: {self.balance:.2f} USDT"
                    )
                    self.current_long_position = None
                    break
            else:
                if current_price <= tp_price:
                    profit = self.balance * settings['tp_percent'] * (leverage / 15)
                    self.short_basarili += 1
                    self.logger.info(f"SHORT pozisyon kapatıldı. Sebep: TP, Kar/Zarar: {profit:.2f} USDT, Yeni Bakiye: {self.balance + profit:.2f} USDT")
                    self.position_profit = profit
                    self.last_trade_profit += profit
                    self.balance += profit
                    self.close_position(position_type, order_size)
                    self.play_sound("islemkapandi.wav")
                    self.send_telegram_message(
                        f"SHORT pozisyon kapatıldı!\nSebep: Take Profit\nKar/Zarar: {profit:.2f} USDT\nYeni Bakiye: {self.balance:.2f} USDT"
                    )
                    self.current_short_position = None
                    break
                elif current_price >= sl_price:
                    loss = -self.balance * settings['sl_percent'] * (leverage / 15)
                    self.short_basarisiz += 1
                    self.logger.info(f"SHORT pozisyon kapatıldı. Sebep: SL, Kar/Zarar: {loss:.2f} USDT, Yeni Bakiye: {self.balance + loss:.2f} USDT")
                    self.position_profit = loss
                    self.last_trade_profit += loss
                    self.balance += loss
                    self.close_position(position_type, order_size)
                    self.play_sound("islemkapandi.wav")
                    self.send_telegram_message(
                        f"SHORT pozisyon kapatıldı!\nSebep: Stop Loss\nKar/Zarar: {loss:.2f} USDT\nYeni Bakiye: {self.balance:.2f} USDT"
                    )
                    self.current_short_position = None
                    break
            time.sleep(3)

    def start_bot(self):
        self.bot_running = True
        self.play_sound("Bot_basladi.wav")
        self.logger.info("Bot başlatıldı")
        self.send_telegram_message(f"Bot başlatıldı!\nSembol: {self.symbol}\nBakiye: {self.balance:.2f} USDT")

    def stop_bot(self):
        self.bot_running = False
        self.found_symbol = None
        self.current_long_position = None
        self.current_short_position = None
        if self.monitor_thread_long:
            self.monitor_thread_long.join()
        if self.monitor_thread_short:
            self.monitor_thread_short.join()
        self.logger.info("Bot durduruldu")
        self.send_telegram_message("Bot durduruldu")

    def update_long_settings(self, **kwargs):
        self.long_settings.update(kwargs)
        self.symbol = self.long_settings['symbol']
        self.found_symbol = None
        self.logger.info(f"Long ayarları güncellendi: {self.long_settings}")

    def update_short_settings(self, **kwargs):
        self.short_settings.update(kwargs)
        self.symbol = self.short_settings['symbol']
        self.found_symbol = None
        self.logger.info(f"Short ayarları güncellendi: {self.short_settings}")

    def set_data_source(self, source):
        self.data_source = source
        self.logger.info(f"Veri kaynağı ayarlandı: {source}")
        self.send_telegram_message(f"Veri kaynağı ayarlandı: {source}")

    def set_mum_sonu_bekle(self, value):
        self.mum_sonu_bekle = value
        self.logger.info(f"Mum sonu bekleme: {value}")
        self.send_telegram_message(f"Mum sonu bekleme: {value}")

    def set_disable_position(self, value):
        self.disable_position = value
        self.logger.info(f"Devre Dışı Bırakma Ayarı: {value}")
        self.send_telegram_message(f"Devre Dışı Bırakma Ayarı: {value}")

if __name__ == "__main__":
    bot = BotLogic()
    bot.start_bot()