import os
import json
from datetime import datetime
from gate_api import ApiClient, Configuration, FuturesApi
from binance.client import Client as BinanceClient
import logging

class ExchangeManager:
    def __init__(self, api_key, api_secret, exchange_name, log_file):
        self.exchange_name = exchange_name.lower()
        self.log_file = log_file
        self.logger = logging.getLogger('BotLogger')
        self.coin_list_cache = None
        self.last_fetch_date = None

        if self.exchange_name == "gateio":
            self.config = Configuration(key=api_key, secret=api_secret)
            self.exchange = FuturesApi(ApiClient(self.config))
        elif self.exchange_name == "binance":
            self.exchange = BinanceClient(api_key, api_secret)
        else:
            raise ValueError(f"Desteklenmeyen borsa: {exchange_name}")

    def check_symbol_exists(self, symbol):
        try:
            if self.exchange_name == "gateio":
                settle = "usdt"
                contracts = self.exchange.list_futures_contracts(settle)
                return any(contract.name == symbol for contract in contracts)
            elif self.exchange_name == "binance":
                symbol = symbol.replace("_USDT", "USDT")
                markets = self.exchange.get_exchange_info()['symbols']
                return any(market['symbol'] == symbol for market in markets)
        except Exception as e:
            self.logger.error(f"[exchange.py:ExchangeManager.check_symbol_exists] Sembol kontrol hatası: {e}")
            return False

    def get_balance(self):
        try:
            if self.exchange_name == "gateio":
                settle = "usdt"
                account = self.exchange.list_futures_accounts(settle=settle)
                return float(account[0].total) if account else 0.0
            elif self.exchange_name == "binance":
                account = self.exchange.get_account()
                for asset in account['balances']:
                    if asset['asset'] == 'USDT':
                        return float(asset['free']) + float(asset['locked'])
                return 0.0
        except Exception as e:
            self.logger.error(f"[exchange.py:ExchangeManager.get_balance] Bakiye alınamadı: {e}")
            return 0.0

    def get_coin_list(self):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            coin_list_file = "coinlist.json"
            if os.path.exists(coin_list_file):
                with open(coin_list_file, 'r') as f:
                    data = json.load(f)
                    if data.get('date') == today and 'coins' in data:
                        self.coin_list_cache = data['coins']
                        self.last_fetch_date = today
                        self.logger.info(f"[exchange.py:ExchangeManager.get_coin_list] Coin listesi {today} için coinlist.json'dan alındı: {len(self.coin_list_cache)} coin")
                        return self.coin_list_cache
            if self.coin_list_cache is None or self.last_fetch_date != today:
                if self.exchange_name == "gateio":
                    settle = "usdt"
                    contracts = self.exchange.list_futures_contracts(settle)
                    self.coin_list_cache = [contract.name for contract in contracts if contract.name.endswith('_USDT')]
                elif self.exchange_name == "binance":
                    markets = self.exchange.get_exchange_info()['symbols']
                    self.coin_list_cache = [market['symbol'].replace("USDT", "_USDT") for market in markets if market['symbol'].endswith('USDT') and market['status'] == 'TRADING']
                self.last_fetch_date = today
                with open(coin_list_file, 'w') as f:
                    json.dump({'date': today, 'coins': self.coin_list_cache}, f)
                self.logger.info(f"[exchange.py:ExchangeManager.get_coin_list] Coin listesi {self.exchange_name}'dan çekildi ve coinlist.json'a kaydedildi: {len(self.coin_list_cache)} coin")
            return self.coin_list_cache
        except Exception as e:
            self.logger.error(f"[exchange.py:ExchangeManager.get_coin_list] Coin listesi alınamadı: {e}")
            return []