"""
Trading Strategy Module

This module implements the core trading strategy logic:
- RSI(6) and Bollinger Band based signals
- Position management (entry/exit logic)
- Risk management calculations
- Strategy configuration handling

The strategy opens long positions when:
- RSI(6) < configured threshold AND
- Price is below Bollinger Band lower band by configured percentage
"""

import logging
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from ..indicators.technical_indicators import TechnicalIndicators


class TradingStrategy:
    """
    Main trading strategy class implementing RSI + Bollinger Band strategy
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize trading strategy with configuration
        
        Args:
            config (Dict[str, Any]): Strategy configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.indicators = TechnicalIndicators()
        
        self.rsi_period = 6
        self.bb_period = 20
        self.bb_std_dev = 2.0
        
    def analyze_symbol(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a symbol's data and generate trading signals
        
        Args:
            symbol (str): Trading symbol
            df (pd.DataFrame): OHLCV data
            
        Returns:
            Dict[str, Any]: Analysis results including signals and indicator values
        """
        if len(df) < max(self.rsi_period, self.bb_period):
            self.logger.warning(f"Insufficient data for {symbol}: {len(df)} candles")
            return {
                'symbol': symbol,
                'signal': 'NONE',
                'reason': 'Insufficient data',
                'rsi': None,
                'bb_upper': None,
                'bb_middle': None,
                'bb_lower': None,
                'current_price': None
            }
        
        rsi = self.indicators.calculate_rsi(df['close'], self.rsi_period)
        bb_upper, bb_middle, bb_lower = self.indicators.calculate_bollinger_bands(
            df['close'], self.bb_period, self.bb_std_dev
        )
        
        current_price = df['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]
        current_bb_upper = bb_upper.iloc[-1]
        current_bb_middle = bb_middle.iloc[-1]
        
        symbol_config = self.config.get('pairs', {}).get(symbol, {})
        
        if not symbol_config or not symbol_config.get('enabled', False):
            return {
                'symbol': symbol,
                'signal': 'NONE',
                'reason': 'Symbol not configured or disabled',
                'rsi': current_rsi,
                'bb_upper': current_bb_upper,
                'bb_middle': current_bb_middle,
                'bb_lower': current_bb_lower,
                'current_price': current_price
            }
        
        rsi_threshold = symbol_config.get('rsi_long_threshold', 30)
        distance_threshold = symbol_config.get('shadow_distance_threshold', 1.5)
        
        is_long_signal = self.indicators.is_long_signal(
            current_rsi, current_price, current_bb_lower,
            rsi_threshold, distance_threshold
        )
        
        distance_from_bb = self.indicators.calculate_price_distance_from_bb_lower(
            current_price, current_bb_lower
        )
        
        signal = 'NONE'
        reason = 'No signal'
        
        if is_long_signal:
            signal = 'LONG'
            reason = f'RSI({current_rsi:.2f}) < {rsi_threshold} AND price {distance_from_bb:.2f}% below BB lower'
        else:
            reasons = []
            if current_rsi >= rsi_threshold:
                reasons.append(f'RSI({current_rsi:.2f}) >= {rsi_threshold}')
            if distance_from_bb < distance_threshold:
                reasons.append(f'Price only {distance_from_bb:.2f}% below BB (need {distance_threshold}%)')
            reason = ' AND '.join(reasons) if reasons else 'No signal conditions met'
        
        return {
            'symbol': symbol,
            'signal': signal,
            'reason': reason,
            'rsi': current_rsi,
            'bb_upper': current_bb_upper,
            'bb_middle': current_bb_middle,
            'bb_lower': current_bb_lower,
            'current_price': current_price,
            'distance_from_bb_lower': distance_from_bb,
            'config': symbol_config
        }
    
    def calculate_position_size(self, symbol: str, current_price: float) -> float:
        """
        Calculate position size based on configuration
        
        Args:
            symbol (str): Trading symbol
            current_price (float): Current price
            
        Returns:
            float: Position size in base asset
        """
        symbol_config = self.config.get('pairs', {}).get(symbol, {})
        trade_volume_usdt = symbol_config.get('trade_volume', 20)
        
        quantity = trade_volume_usdt / current_price
        
        return quantity
    
    def calculate_take_profit_stop_loss(self, symbol: str, entry_price: float, side: str) -> Tuple[float, float]:
        """
        Calculate take profit and stop loss prices
        
        Args:
            symbol (str): Trading symbol
            entry_price (float): Entry price
            side (str): Position side ('LONG' or 'SHORT')
            
        Returns:
            Tuple[float, float]: (take_profit_price, stop_loss_price)
        """
        symbol_config = self.config.get('pairs', {}).get(symbol, {})
        tp_percent = symbol_config.get('take_profit_percent', 2.0) / 100
        sl_percent = symbol_config.get('stop_loss_percent', 1.0) / 100
        
        if side.upper() == 'LONG':
            take_profit = entry_price * (1 + tp_percent)
            stop_loss = entry_price * (1 - sl_percent)
        else:  # SHORT
            take_profit = entry_price * (1 - tp_percent)
            stop_loss = entry_price * (1 + sl_percent)
        
        return take_profit, stop_loss
    
    def should_close_position(self, symbol: str, position_data: Dict[str, Any], 
                            current_price: float) -> Tuple[bool, str]:
        """
        Check if a position should be closed based on take profit or stop loss
        
        Args:
            symbol (str): Trading symbol
            position_data (Dict[str, Any]): Position information
            current_price (float): Current market price
            
        Returns:
            Tuple[bool, str]: (should_close, reason)
        """
        entry_price = float(position_data.get('entry_price', 0))
        side = position_data.get('side', 'LONG')
        
        if entry_price == 0:
            return False, 'No entry price available'
        
        take_profit, stop_loss = self.calculate_take_profit_stop_loss(symbol, entry_price, side)
        
        if side.upper() == 'LONG':
            if current_price >= take_profit:
                return True, 'Take Profit'
            elif current_price <= stop_loss:
                return True, 'Stop Loss'
        else:  # SHORT
            if current_price <= take_profit:
                return True, 'Take Profit'
            elif current_price >= stop_loss:
                return True, 'Stop Loss'
        
        return False, 'No exit signal'
    
    def get_enabled_symbols(self) -> list:
        """
        Get list of enabled trading symbols from configuration
        
        Returns:
            list: List of enabled symbols
        """
        enabled_symbols = []
        pairs_config = self.config.get('pairs', {})
        
        for symbol, config in pairs_config.items():
            if config.get('enabled', False):
                enabled_symbols.append(symbol)
        
        return enabled_symbols
    
    def validate_symbol_config(self, symbol: str) -> Tuple[bool, str]:
        """
        Validate symbol configuration
        
        Args:
            symbol (str): Trading symbol
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        symbol_config = self.config.get('pairs', {}).get(symbol, {})
        
        if not symbol_config:
            return False, f"No configuration found for {symbol}"
        
        required_fields = [
            'leverage', 'shadow_distance_threshold', 'trade_volume',
            'rsi_long_threshold', 'take_profit_percent', 'stop_loss_percent'
        ]
        
        for field in required_fields:
            if field not in symbol_config:
                return False, f"Missing required field '{field}' for {symbol}"
            
            value = symbol_config[field]
            if not isinstance(value, (int, float)) or value <= 0:
                return False, f"Invalid value for '{field}' in {symbol}: {value}"
        
        if symbol_config['leverage'] > 125:
            return False, f"Leverage too high for {symbol}: {symbol_config['leverage']}"
        
        if symbol_config['rsi_long_threshold'] >= 100:
            return False, f"RSI threshold too high for {symbol}: {symbol_config['rsi_long_threshold']}"
        
        return True, "Configuration valid"
