"""
Binance API Client Module

This module handles all interactions with the Binance API including:
- Market data retrieval
- Order placement and management
- Account information
- WebSocket connections for real-time data

Uses python-binance library for API interactions.
"""

import logging
from typing import Dict, List, Optional, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import pandas as pd
from datetime import datetime, timedelta


class BinanceClient:
    """
    Wrapper class for Binance API operations
    """
    
    def __init__(self, api_key: str, secret_key: str, testnet: bool = True):
        """
        Initialize Binance client
        
        Args:
            api_key (str): Binance API key
            secret_key (str): Binance secret key
            testnet (bool): Whether to use testnet (default: True for safety)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        
        self.client = Client(
            api_key=api_key,
            api_secret=secret_key,
            testnet=testnet
        )
        
        self.logger = logging.getLogger(__name__)
        
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information
        
        Returns:
            Dict[str, Any]: Account information
        """
        try:
            return self.client.futures_account()
        except BinanceAPIException as e:
            self.logger.error(f"Error getting account info: {e}")
            raise
    
    def get_usdt_perpetual_symbols(self) -> List[str]:
        """
        Get all available USDT perpetual trading pairs
        
        Returns:
            List[str]: List of USDT perpetual symbols
        """
        try:
            exchange_info = self.client.futures_exchange_info()
            symbols = []
            
            for symbol_info in exchange_info['symbols']:
                if (symbol_info['symbol'].endswith('USDT') and 
                    symbol_info['contractType'] == 'PERPETUAL' and
                    symbol_info['status'] == 'TRADING'):
                    symbols.append(symbol_info['symbol'])
            
            return symbols
        except BinanceAPIException as e:
            self.logger.error(f"Error getting symbols: {e}")
            raise
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """
        Get historical kline/candlestick data
        
        Args:
            symbol (str): Trading symbol (e.g., 'BTCUSDT')
            interval (str): Kline interval (e.g., '15m')
            limit (int): Number of klines to retrieve (default: 500)
            
        Returns:
            pd.DataFrame: DataFrame with OHLCV data
        """
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            df.set_index('timestamp', inplace=True)
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except BinanceAPIException as e:
            self.logger.error(f"Error getting klines for {symbol}: {e}")
            raise
    
    def get_current_price(self, symbol: str) -> float:
        """
        Get current price for a symbol
        
        Args:
            symbol (str): Trading symbol
            
        Returns:
            float: Current price
        """
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            raise
    
    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        Set leverage for a symbol
        
        Args:
            symbol (str): Trading symbol
            leverage (int): Leverage value
            
        Returns:
            Dict[str, Any]: Response from API
        """
        try:
            return self.client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )
        except BinanceAPIException as e:
            self.logger.error(f"Error setting leverage for {symbol}: {e}")
            raise
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        """
        Place a market order
        
        Args:
            symbol (str): Trading symbol
            side (str): 'BUY' or 'SELL'
            quantity (float): Order quantity
            
        Returns:
            Dict[str, Any]: Order response
        """
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            self.logger.info(f"Market order placed: {symbol} {side} {quantity}")
            return order
        except (BinanceAPIException, BinanceOrderException) as e:
            self.logger.error(f"Error placing market order: {e}")
            raise
    
    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> Dict[str, Any]:
        """
        Place a limit order
        
        Args:
            symbol (str): Trading symbol
            side (str): 'BUY' or 'SELL'
            quantity (float): Order quantity
            price (float): Order price
            
        Returns:
            Dict[str, Any]: Order response
        """
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                timeInForce='GTC',
                quantity=quantity,
                price=price
            )
            self.logger.info(f"Limit order placed: {symbol} {side} {quantity} @ {price}")
            return order
        except (BinanceAPIException, BinanceOrderException) as e:
            self.logger.error(f"Error placing limit order: {e}")
            raise
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions
        
        Returns:
            List[Dict[str, Any]]: List of open positions
        """
        try:
            positions = self.client.futures_position_information()
            open_positions = [pos for pos in positions if float(pos['positionAmt']) != 0]
            return open_positions
        except BinanceAPIException as e:
            self.logger.error(f"Error getting open positions: {e}")
            raise
    
    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close an open position by placing opposite market order
        
        Args:
            symbol (str): Trading symbol
            
        Returns:
            Dict[str, Any]: Order response
        """
        try:
            positions = self.get_open_positions()
            position = next((pos for pos in positions if pos['symbol'] == symbol), None)
            
            if not position:
                raise ValueError(f"No open position found for {symbol}")
            
            position_amt = float(position['positionAmt'])
            
            if position_amt == 0:
                raise ValueError(f"No position to close for {symbol}")
            
            side = 'SELL' if position_amt > 0 else 'BUY'
            quantity = abs(position_amt)
            
            return self.place_market_order(symbol, side, quantity)
            
        except (BinanceAPIException, BinanceOrderException) as e:
            self.logger.error(f"Error closing position for {symbol}: {e}")
            raise
