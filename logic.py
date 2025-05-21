import os
from dotenv import load_dotenv
from exchange import ExchangeManager
from data_fetcher import DataFetcher
from position_manager import PositionManager
from telegram_notifier import TelegramNotifier
import logging
import pandas as pd
from datetime import datetime

load_dotenv()

class BotLogic:
    def __init__(self):
        self.logger = logging.getLogger('BotLogger')
        self.log_file = 'islem_log.txt'
        self.data_source = "gateio"
        self.exchange = ExchangeManager(
            api_key=os.getenv('GATE_API_KEY') if self.data_source == "gateio" else os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('GATE_API_SECRET') if self.data_source == "gateio" else os.getenv('BINANCE_API_SECRET'),
            exchange_name=self.data_source,
            log_file=self.log_file
        )
        self.data_fetcher = DataFetcher(self.data_source)
        self.position_manager = PositionManager(self.exchange, self.log_file)
        self.telegram_notifier = TelegramNotifier(self.log_file)
        self.bot_running = False
        self.symbol = "DOGE_USDT"
        self.balance = 0.0
        self.last_price = 0.0
        self.last_rsi = 0.0
        self.last_ma7_distance = 0.0
        self.last_trade_profit = 0.0
        self.btc_price = 0.0
        self.eth_price = 0.0
        self.position_profit = 0.0
        self.current_long_position = None
        self.current_short_position = None
        self.long_basarili = 0
        self.long_basarisiz = 0
        self.short_basarili = 0
        self.short_basarisiz = 0
        self.mum_sonu_bekle = False
        self.disable_position = "Hiçbiri"
        # Varsayılan ayarlar
        self.long_settings = {
            'symbol': self.symbol,
            'rsi_condition': "Küçüktür",
            'rsi_threshold': 20.0,
            'tp_percent': 0.01,
            'sl_percent': 0.017,
            'leverage': 15,
            'ma7_threshold': 0.007,
            'bollinger_band_break_pct': 0.0025,
            'volatility_threshold': 0.5,
            'allowed_hours': [1, 9, 11, 17, 19, 22, 23],
            'rsi_period': 6,
            'bb_period': 20,
            'bb_std': 2,
            'ma_period': 7,
            'commission': 0.001
        }
        self.short_settings = {
            'symbol': self.symbol,
            'rsi_condition': "Büyüktür",
            'rsi_threshold': 80.0,
            'tp_percent': 0.01,
            'sl_percent': 0.017,
            'leverage': 15,
            'ma7_threshold': 0.007,
            'bollinger_band_break_pct': 0.0025,
            'volatility_threshold': 0.5,
            'allowed_hours': [1, 9, 11, 17, 19, 22, 23],
            'rsi_period': 6,
            'bb_period': 20,
            'bb_std': 2,
            'ma_period': 7,
            'commission': 0.001
        }
        try:
            self.update_data()
            self.logger.info("BotLogic initialized")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.__init__] Başlatma hatası: {e}")
            self.telegram_notifier.send_message(f"Bot başlatma hatası: {e}")

    def set_data_source(self, source):
        try:
            if source not in ["gateio", "binance"]:
                raise ValueError(f"Geçersiz veri kaynağı: {source}")
            self.data_source = source
            self.exchange = ExchangeManager(
                api_key=os.getenv('GATE_API_KEY') if source == "gateio" else os.getenv('BINANCE_API_KEY'),
                api_secret=os.getenv('GATE_API_SECRET') if source == "gateio" else os.getenv('BINANCE_API_SECRET'),
                exchange_name=source,
                log_file=self.log_file
            )
            self.data_fetcher = DataFetcher(source)
            self.position_manager = PositionManager(self.exchange, self.log_file)
            self.logger.info(f"Veri kaynağı {source} olarak ayarlandı")
            self.telegram_notifier.send_message(f"Veri kaynağı {source} olarak ayarlandı")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.set_data_source] Veri kaynağı ayarlama hatası: {e}")
            self.telegram_notifier.send_message(f"Veri kaynağı ayarlama hatası: {e}")

    def set_mum_sonu_bekle(self, value):
        try:
            self.mum_sonu_bekle = value
            self.logger.info(f"Mum sonu bekleme: {value}")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.set_mum_sonu_bekle] Mum sonu ayarlama hatası: {e}")

    def set_disable_position(self, value):
        try:
            if value not in ["Hiçbiri", "Long", "Short"]:
                raise ValueError(f"Geçersiz devre dışı seçeneği: {value}")
            self.disable_position = value
            self.logger.info(f"Devre dışı pozisyon: {value}")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.set_disable_position] Devre dışı ayarlama hatası: {e}")

    def update_long_settings(self, **kwargs):
        try:
            for key, value in kwargs.items():
                if key in self.long_settings:
                    self.long_settings[key] = value
            self.symbol = self.long_settings['symbol']
            self.logger.info(f"Long ayarları güncellendi: {self.long_settings}")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.update_long_settings] Long ayarları güncelleme hatası: {e}")

    def update_short_settings(self, **kwargs):
        try:
            for key, value in kwargs.items():
                if key in self.short_settings:
                    self.short_settings[key] = value
            self.symbol = self.short_settings['symbol']
            self.logger.info(f"Short ayarları güncellendi: {self.short_settings}")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.update_short_settings] Short ayarları güncelleme hatası: {e}")

    def save_selected_coins(self, long_coin, short_coin):
        try:
            self.long_settings['symbol'] = long_coin.split('_')[0]
            self.short_settings['symbol'] = short_coin.split('_')[0]
            self.symbol = self.long_settings['symbol']
            self.logger.info(f"Seçilen coin'ler kaydedildi: Long={long_coin}, Short={short_coin}")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.save_selected_coins] Coin kaydetme hatası: {e}")

    def get_coin_list(self):
        try:
            return self.exchange.get_coin_list()
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.get_coin_list] Coin listesi alınamadı: {e}")
            return []

    def update_data(self):
        try:
            self.balance = self.exchange.get_balance()
            df = self.data_fetcher.fetch_klines(self.symbol)
            if not df.empty:
                indicators = self.data_fetcher.calculate_indicators(df)
                self.last_price = float(df['close'].iloc[-1])
                self.last_rsi = indicators.get('rsi', 0.0)
                self.last_ma7_distance = indicators.get('ma7_distance', 0.0)
                btc_df = self.data_fetcher.fetch_klines("BTC_USDT")
                eth_df = self.data_fetcher.fetch_klines("ETH_USDT")
                self.btc_price = float(btc_df['close'].iloc[-1]) if not btc_df.empty else 0.0
                self.eth_price = float(eth_df['close'].iloc[-1]) if not eth_df.empty else 0.0
                if self.current_long_position or self.current_short_position:
                    self.position_profit = self.position_manager.calculate_position_profit(
                        self.current_long_position or self.current_short_position, self.last_price
                    )
            self.logger.debug("Veriler güncellendi")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.update_data] Veri güncelleme hatası: {e}")
            self.telegram_notifier.send_message(f"Veri güncelleme hatası: {e}")

    def start_bot(self):
        try:
            if not self.exchange.check_symbol_exists(self.symbol):
                raise ValueError(f"Geçersiz sembol: {self.symbol}")
            self.bot_running = True
            self.logger.info("Bot başlatıldı")
            self.telegram_notifier.send_message("Bot başlatıldı")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.start_bot] Bot başlatma hatası: {e}")
            self.telegram_notifier.send_message(f"Bot başlatma hatası: {e}")

    def stop_bot(self):
        try:
            self.bot_running = False
            self.logger.info("Bot durduruldu")
            self.telegram_notifier.send_message("Bot durduruldu")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.stop_bot] Bot durdurma hatası: {e}")
            self.telegram_notifier.send_message(f"Bot durdurma hatası: {e}")

    def trade_logic(self):
        try:
            if not self.bot_running:
                return
            current_hour = datetime.now().hour
            if self.long_settings['allowed_hours'] and current_hour not in self.long_settings['allowed_hours']:
                self.logger.debug(f"Saat {current_hour}: İşlem saatleri dışında")
                return
            df = self.data_fetcher.fetch_klines(self.symbol)
            if df.empty:
                self.logger.warning("Kline verisi alınamadı")
                return
            indicators = self.data_fetcher.calculate_indicators(df)
            rsi = indicators.get('rsi', 0.0)
            ma7_distance = indicators.get('ma7_distance', 0.0)
            bollinger_break = indicators.get('bollinger_break', 0.0)
            volatility = indicators.get('volatility', 0.0)

            # Long mantığı
            if self.disable_position != "Long":
                long_conditions = []
                if self.long_settings['rsi_threshold'] is not None:
                    rsi_condition = (rsi < self.long_settings['rsi_threshold'] if self.long_settings['rsi_condition'] == "Küçüktür" else
                                     rsi > self.long_settings['rsi_threshold'])
                    long_conditions.append(rsi_condition)
                if self.long_settings['ma7_threshold'] is not None:
                    long_conditions.append(abs(ma7_distance) > self.long_settings['ma7_threshold'])
                if self.long_settings['bollinger_band_break_pct'] is not None:
                    long_conditions.append(abs(bollinger_break) > self.long_settings['bollinger_band_break_pct'])
                if self.long_settings['volatility_threshold'] is not None:
                    long_conditions.append(volatility > self.long_settings['volatility_threshold'])
                if all(long_conditions) and not self.current_long_position:
                    amount = self.balance * 0.1
                    leverage = self.long_settings['leverage'] or 1
                    position = self.position_manager.open_position(self.symbol, "long", amount, leverage)
                    if position:
                        self.current_long_position = position
                        self.telegram_notifier.send_message(f"Long pozisyon açıldı: {self.symbol}, miktar: {amount}")

            # Short mantığı
            if self.disable_position != "Short":
                short_conditions = []
                if self.short_settings['rsi_threshold'] is not None:
                    rsi_condition = (rsi > self.short_settings['rsi_threshold'] if self.short_settings['rsi_condition'] == "Büyüktür" else
                                     rsi < self.short_settings['rsi_threshold'])
                    short_conditions.append(rsi_condition)
                if self.short_settings['ma7_threshold'] is not None:
                    short_conditions.append(abs(ma7_distance) > self.short_settings['ma7_threshold'])
                if self.short_settings['bollinger_band_break_pct'] is not None:
                    short_conditions.append(abs(bollinger_break) > self.short_settings['bollinger_band_break_pct'])
                if self.short_settings['volatility_threshold'] is not None:
                    short_conditions.append(volatility > self.short_settings['volatility_threshold'])
                if all(short_conditions) and not self.current_short_position:
                    amount = self.balance * 0.1
                    leverage = self.short_settings['leverage'] or 1
                    position = self.position_manager.open_position(self.symbol, "short", amount, leverage)
                    if position:
                        self.current_short_position = position
                        self.telegram_notifier.send_message(f"Short pozisyon açıldı: {self.symbol}, miktar: {amount}")

            # Pozisyon kapatma
            if self.current_long_position:
                profit = self.position_manager.calculate_position_profit(self.current_long_position, self.last_price)
                if (self.long_settings['tp_percent'] and profit >= self.long_settings['tp_percent'] * self.balance) or \
                   (self.long_settings['sl_percent'] and profit <= -self.long_settings['sl_percent'] * self.balance):
                    self.position_manager.close_position(self.current_long_position, self.last_price)
                    self.last_trade_profit = profit
                    if profit > 0:
                        self.long_basarili += 1
                    else:
                        self.long_basarisiz += 1
                    self.current_long_position = None
                    self.telegram_notifier.send_message(f"Long pozisyon kapandı, kar: {profit:.2f} USDT")

            if self.current_short_position:
                profit = self.position_manager.calculate_position_profit(self.current_short_position, self.last_price)
                if (self.short_settings['tp_percent'] and profit >= self.short_settings['tp_percent'] * self.balance) or \
                   (self.short_settings['sl_percent'] and profit <= -self.short_settings['sl_percent'] * self.balance):
                    self.position_manager.close_position(self.current_short_position, self.last_price)
                    self.last_trade_profit = profit
                    if profit > 0:
                        self.short_basarili += 1
                    else:
                        self.short_basarisiz += 1
                    self.current_short_position = None
                    self.telegram_notifier.send_message(f"Short pozisyon kapandı, kar: {profit:.2f} USDT")

            self.logger.debug("Trade mantığı çalıştı")
        except Exception as e:
            self.logger.error(f"[logic.py:BotLogic.trade_logic] Trade mantığı hatası: {e}")
            self.telegram_notifier.send_message(f"Trade mantığı hatası: {e}")