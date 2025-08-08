"""
Telegram Notification Module

This module handles sending notifications to Telegram about trading events:
- Position opened/closed
- Entry/exit prices
- RSI values at entry
- Profit/loss information

Uses python-telegram-bot library for sending messages.
"""

import logging
from typing import Dict, Any, Optional
import asyncio
from telegram import Bot
from telegram.error import TelegramError


class TelegramNotifier:
    """
    Class for sending trading notifications via Telegram
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier
        
        Args:
            bot_token (str): Telegram bot token
            chat_id (str): Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token) if bot_token else None
        self.logger = logging.getLogger(__name__)
        
        self.enabled = bool(bot_token and chat_id)
        
        if not self.enabled:
            self.logger.warning("Telegram notifications disabled - missing bot token or chat ID")
    
    async def send_message(self, message: str) -> bool:
        """
        Send a message to Telegram
        
        Args:
            message (str): Message to send
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not self.enabled:
            self.logger.info(f"Telegram notification (disabled): {message}")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            self.logger.info("Telegram message sent successfully")
            return True
        except TelegramError as e:
            self.logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def send_message_sync(self, message: str) -> bool:
        """
        Synchronous wrapper for sending messages
        
        Args:
            message (str): Message to send
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not self.enabled:
            self.logger.info(f"Telegram notification (disabled): {message}")
            return False
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.send_message(message))
            loop.close()
            return result
        except Exception as e:
            self.logger.error(f"Error in sync message sending: {e}")
            return False
    
    def format_position_opened_message(self, symbol: str, side: str, quantity: float, 
                                     entry_price: float, leverage: int, rsi: float,
                                     take_profit: float, stop_loss: float) -> str:
        """
        Format message for position opened event
        
        Args:
            symbol (str): Trading symbol
            side (str): Position side (LONG/SHORT)
            quantity (float): Position quantity
            entry_price (float): Entry price
            leverage (int): Leverage used
            rsi (float): RSI value at entry
            take_profit (float): Take profit price
            stop_loss (float): Stop loss price
            
        Returns:
            str: Formatted message
        """
        message = f"""
🚀 <b>POSITION OPENED</b>

📊 <b>Symbol:</b> {symbol}
📈 <b>Side:</b> {side}
💰 <b>Quantity:</b> {quantity:.6f}
💵 <b>Entry Price:</b> ${entry_price:.6f}
⚡ <b>Leverage:</b> {leverage}x
📉 <b>RSI at Entry:</b> {rsi:.2f}

🎯 <b>Take Profit:</b> ${take_profit:.6f}
🛑 <b>Stop Loss:</b> ${stop_loss:.6f}

⏰ <b>Time:</b> {asyncio.get_event_loop().time()}
        """.strip()
        
        return message
    
    def format_position_closed_message(self, symbol: str, side: str, quantity: float,
                                     entry_price: float, exit_price: float,
                                     pnl: float, pnl_percent: float, reason: str) -> str:
        """
        Format message for position closed event
        
        Args:
            symbol (str): Trading symbol
            side (str): Position side (LONG/SHORT)
            quantity (float): Position quantity
            entry_price (float): Entry price
            exit_price (float): Exit price
            pnl (float): Profit/Loss in USDT
            pnl_percent (float): Profit/Loss percentage
            reason (str): Reason for closing (TP/SL/Manual)
            
        Returns:
            str: Formatted message
        """
        pnl_emoji = "💚" if pnl >= 0 else "❌"
        
        message = f"""
{pnl_emoji} <b>POSITION CLOSED</b>

📊 <b>Symbol:</b> {symbol}
📈 <b>Side:</b> {side}
💰 <b>Quantity:</b> {quantity:.6f}
📥 <b>Entry Price:</b> ${entry_price:.6f}
📤 <b>Exit Price:</b> ${exit_price:.6f}

{pnl_emoji} <b>PnL:</b> ${pnl:.2f} ({pnl_percent:+.2f}%)
🔄 <b>Reason:</b> {reason}

⏰ <b>Time:</b> {asyncio.get_event_loop().time()}
        """.strip()
        
        return message
    
    def notify_position_opened(self, symbol: str, side: str, quantity: float,
                             entry_price: float, leverage: int, rsi: float,
                             take_profit: float, stop_loss: float) -> bool:
        """
        Send notification for opened position
        
        Args:
            symbol (str): Trading symbol
            side (str): Position side
            quantity (float): Position quantity
            entry_price (float): Entry price
            leverage (int): Leverage used
            rsi (float): RSI value at entry
            take_profit (float): Take profit price
            stop_loss (float): Stop loss price
            
        Returns:
            bool: True if notification sent successfully
        """
        message = self.format_position_opened_message(
            symbol, side, quantity, entry_price, leverage, rsi, take_profit, stop_loss
        )
        return self.send_message_sync(message)
    
    def notify_position_closed(self, symbol: str, side: str, quantity: float,
                             entry_price: float, exit_price: float,
                             pnl: float, pnl_percent: float, reason: str) -> bool:
        """
        Send notification for closed position
        
        Args:
            symbol (str): Trading symbol
            side (str): Position side
            quantity (float): Position quantity
            entry_price (float): Entry price
            exit_price (float): Exit price
            pnl (float): Profit/Loss in USDT
            pnl_percent (float): Profit/Loss percentage
            reason (str): Reason for closing
            
        Returns:
            bool: True if notification sent successfully
        """
        message = self.format_position_closed_message(
            symbol, side, quantity, entry_price, exit_price, pnl, pnl_percent, reason
        )
        return self.send_message_sync(message)
    
    def notify_error(self, error_message: str) -> bool:
        """
        Send error notification
        
        Args:
            error_message (str): Error message to send
            
        Returns:
            bool: True if notification sent successfully
        """
        message = f"⚠️ <b>TRADING BOT ERROR</b>\n\n{error_message}"
        return self.send_message_sync(message)
