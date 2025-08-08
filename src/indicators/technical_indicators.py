"""
Technical Indicators Module

This module contains implementations of technical indicators used in the trading strategy:
- RSI (Relative Strength Index)
- Bollinger Bands

All indicators are calculated using pandas and numpy for efficient computation.
"""

import pandas as pd
import numpy as np
from typing import Tuple


class TechnicalIndicators:
    """
    A class containing static methods for calculating technical indicators
    """
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 6) -> pd.Series:
        """
        Calculate the Relative Strength Index (RSI)
        
        Args:
            prices (pd.Series): Series of closing prices
            period (int): Period for RSI calculation (default: 6)
            
        Returns:
            pd.Series: RSI values
        """
        delta = prices.diff()
        
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        avg_gains = gains.rolling(window=period, min_periods=1).mean()
        avg_losses = losses.rolling(window=period, min_periods=1).mean()
        
        rs = avg_gains / (avg_losses + 1e-10)
        
        rsi = 100 - (100 / (1 + rs))
        
        rsi = rsi.fillna(50)  # Fill NaN with neutral RSI
        
        return rsi
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Args:
            prices (pd.Series): Series of closing prices
            period (int): Period for moving average calculation (default: 20)
            std_dev (float): Number of standard deviations for bands (default: 2.0)
            
        Returns:
            Tuple[pd.Series, pd.Series, pd.Series]: (upper_band, middle_band, lower_band)
        """
        middle_band = prices.rolling(window=period).mean()
        
        std = prices.rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def calculate_price_distance_from_bb_lower(price: float, lower_band: float) -> float:
        """
        Calculate the percentage distance of price below the lower Bollinger Band
        
        Args:
            price (float): Current price
            lower_band (float): Lower Bollinger Band value
            
        Returns:
            float: Percentage distance below lower band (positive if below, negative if above)
        """
        if lower_band == 0:
            return 0
        
        distance_percent = ((lower_band - price) / lower_band) * 100
        return distance_percent
    
    @staticmethod
    def is_long_signal(rsi: float, price: float, lower_band: float, 
                      rsi_threshold: float, distance_threshold: float) -> bool:
        """
        Check if conditions are met for a long position signal
        
        Args:
            rsi (float): Current RSI value
            price (float): Current price
            lower_band (float): Lower Bollinger Band value
            rsi_threshold (float): RSI threshold for long entry
            distance_threshold (float): Required percentage below lower band
            
        Returns:
            bool: True if long signal conditions are met
        """
        rsi_condition = rsi < rsi_threshold
        
        distance = TechnicalIndicators.calculate_price_distance_from_bb_lower(price, lower_band)
        distance_condition = distance >= distance_threshold
        
        return rsi_condition and distance_condition
