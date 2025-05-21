import logging
from datetime import datetime

class PositionManager:
    def __init__(self, exchange, log_file):
        self.exchange = exchange
        self.logger = logging.getLogger('BotLogger')
        self.log_file = log_file

    def open_position(self, symbol, position_type, amount, leverage):
        try:
            if self.exchange.exchange_name == "gateio":
                settle = "usdt"
                side = "buy" if position_type == "long" else "sell"
                order = self.exchange.create_futures_order(
                    settle=settle,
                    contract=symbol,
                    size=int(amount),
                    leverage=leverage,
                    side=side
                )
                self.logger.info(f"{position_type.upper()} pozisyon açıldı: {symbol}, miktar: {amount}, kaldıraç: {leverage}x")
                return order
            elif self.exchange.exchange_name == "binance":
                symbol = symbol.replace("_USDT", "USDT")
                side = "BUY" if position_type == "long" else "SELL"
                self.exchange.set_leverage(symbol=symbol, leverage=leverage)
                order = self.exchange.create_market_order(
                    symbol=symbol,
                    side=side,
                    type="MARKET",
                    quantity=amount
                )
                self.logger.info(f"{position_type.upper()} pozisyon açıldı: {symbol}, miktar: {amount}, kaldıraç: {leverage}x")
                return order
        except Exception as e:
            self.logger.error(f"[position_manager.py:PositionManager.open_position] Pozisyon açma hatası: {e}")
            return None

    def close_position(self, position, current_price):
        try:
            symbol = position['symbol']
            amount = position['amount']
            position_type = position['type']
            if self.exchange.exchange_name == "gateio":
                settle = "usdt"
                side = "sell" if position_type == "long" else "buy"
                order = self.exchange.create_futures_order(
                    settle=settle,
                    contract=symbol,
                    size=-int(amount),
                    side=side
                )
                self.logger.info(f"{position_type.upper()} pozisyon kapandı: {symbol}, miktar: {amount}")
                return order
            elif self.exchange.exchange_name == "binance":
                symbol = symbol.replace("_USDT", "USDT")
                side = "SELL" if position_type == "long" else "BUY"
                order = self.exchange.create_market_order(
                    symbol=symbol,
                    side=side,
                    type="MARKET",
                    quantity=amount
                )
                self.logger.info(f"{position_type.upper()} pozisyon kapandı: {symbol}, miktar: {amount}")
                return order
        except Exception as e:
            self.logger.error(f"[position_manager.py:PositionManager.close_position] Pozisyon kapatma hatası: {e}")
            return None

    def calculate_position_profit(self, position, current_price):
        try:
            entry_price = position['entry_price']
            amount = position['amount']
            leverage = position['leverage']
            position_type = position['type']
            if position_type == "long":
                profit = (current_price - entry_price) * amount * leverage
            else:
                profit = (entry_price - current_price) * amount * leverage
            return profit
        except Exception as e:
            self.logger.error(f"[position_manager.py:PositionManager.calculate_position_profit] Kar hesaplama hatası: {e}")
            return 0.0