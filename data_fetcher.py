import pandas as pd
from gate_api import SpotApi, ApiClient, Configuration
from binance.client import Client as BinanceClient
import logging
import os
from dotenv import load_dotenv
import ta

load_dotenv()

class DataFetcher:
    def __init__(self, data_source):
        self.data_source = data_source.lower()
        self.logger = logging.getLogger('BotLogger')
        if self.data_source == "gateio":
            self.config = Configuration(key=os.getenv('GATE_API_KEY'), secret=os.getenv('GATE_API_SECRET'))
            self.client = SpotApi(ApiClient(self.config))
        elif self.data_source == "binance":
            self.client = BinanceClient(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))
        else:
            raise ValueError(f"Geçersiz veri kaynağı: {self.data_source}")

    def fetch_klines(self, symbol, interval="15m", limit=100):
        try:
            if self.data_source == "gateio":
                symbol = symbol.replace("_USDT", "_usdt")
                klines = self.client.list_candlesticks(symbol, interval=interval, limit=limit)
                df = pd.DataFrame(klines, columns=['time', 'volume', 'close', 'high', 'low', 'open', 'amount'])
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df[['volume', 'close', 'high', 'low', 'open']] = df[['volume', 'close', 'high', 'low', 'open']].astype(float)
            elif self.data_source == "binance":
                symbol = symbol.replace("_USDT", "USDT")
                klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
                df = pd.DataFrame(klines, columns=[
                    'time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                    'quote_asset_volume', 'number_of_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
                ])
                df['time'] = pd.to_datetime(df['time'], unit='ms')
                df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            return df
        except Exception as e:
            self.logger.error(f"[data_fetcher.py:DataFetcher.fetch_klines] Klines alınamadı: {e}")
            return pd.DataFrame()

    def calculate_indicators(self, df):
        try:
            indicators = {}
            indicators['rsi'] = ta.momentum.RSIIndicator(df['close'], window=6).rsi()
            ma7 = df['close'].rolling(window=7).mean()
            indicators['ma7_distance'] = (df['close'] - ma7) / ma7
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            indicators['bollinger_break'] = (df['close'] - bb.bollinger_hband()) / df['close']
            volatility = df['close'].pct_change().rolling(window=20).std() * 100
            indicators['volatility'] = volatility
            return indicators
        except Exception as e:
            self.logger.error(f"[data_fetcher.py:DataFetcher.calculate_indicators] Göstergeler hesaplanamadı: {e}")
            return {}