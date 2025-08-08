"""
Position Manager Module

This module handles position tracking and management:
- Track open positions
- Calculate profit/loss
- Manage position lifecycle
- Risk management checks

Maintains an in-memory record of positions for the trading bot.
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime


class PositionManager:
    """
    Class for managing trading positions
    """
    
    def __init__(self, positions_file: str = "logs/positions.json"):
        """
        Initialize position manager
        
        Args:
            positions_file (str): File to store position data
        """
        self.positions_file = positions_file
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
        os.makedirs(os.path.dirname(positions_file), exist_ok=True)
        
        self.load_positions()
    
    def load_positions(self) -> None:
        """
        Load positions from file
        """
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r') as f:
                    self.positions = json.load(f)
                self.logger.info(f"Loaded {len(self.positions)} positions from file")
            else:
                self.positions = {}
                self.logger.info("No existing positions file found, starting fresh")
        except Exception as e:
            self.logger.error(f"Error loading positions: {e}")
            self.positions = {}
    
    def save_positions(self) -> None:
        """
        Save positions to file
        """
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=2, default=str)
            self.logger.debug("Positions saved to file")
        except Exception as e:
            self.logger.error(f"Error saving positions: {e}")
    
    def add_position(self, symbol: str, side: str, quantity: float, entry_price: float,
                    leverage: int, take_profit: float, stop_loss: float, rsi_at_entry: float) -> str:
        """
        Add a new position
        
        Args:
            symbol (str): Trading symbol
            side (str): Position side (LONG/SHORT)
            quantity (float): Position quantity
            entry_price (float): Entry price
            leverage (int): Leverage used
            take_profit (float): Take profit price
            stop_loss (float): Stop loss price
            rsi_at_entry (float): RSI value at entry
            
        Returns:
            str: Position ID
        """
        position_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        position_data = {
            'id': position_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': entry_price,
            'leverage': leverage,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'rsi_at_entry': rsi_at_entry,
            'entry_time': datetime.now().isoformat(),
            'status': 'OPEN',
            'exit_price': None,
            'exit_time': None,
            'pnl': 0.0,
            'pnl_percent': 0.0,
            'exit_reason': None
        }
        
        self.positions[position_id] = position_data
        self.save_positions()
        
        self.logger.info(f"Added new position: {position_id} - {symbol} {side} {quantity}")
        return position_id
    
    def close_position(self, position_id: str, exit_price: float, reason: str) -> Dict[str, Any]:
        """
        Close a position and calculate PnL
        
        Args:
            position_id (str): Position ID
            exit_price (float): Exit price
            reason (str): Reason for closing
            
        Returns:
            Dict[str, Any]: Updated position data
        """
        if position_id not in self.positions:
            raise ValueError(f"Position {position_id} not found")
        
        position = self.positions[position_id]
        
        if position['status'] != 'OPEN':
            raise ValueError(f"Position {position_id} is not open")
        
        entry_price = position['entry_price']
        quantity = position['quantity']
        side = position['side']
        leverage = position['leverage']
        
        if side.upper() == 'LONG':
            price_change = exit_price - entry_price
        else:  # SHORT
            price_change = entry_price - exit_price
        
        pnl = (price_change / entry_price) * quantity * entry_price * leverage
        pnl_percent = (price_change / entry_price) * 100 * leverage
        
        position.update({
            'exit_price': exit_price,
            'exit_time': datetime.now().isoformat(),
            'status': 'CLOSED',
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'exit_reason': reason
        })
        
        self.save_positions()
        
        self.logger.info(f"Closed position: {position_id} - PnL: ${pnl:.2f} ({pnl_percent:+.2f}%)")
        return position
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions
        
        Returns:
            List[Dict[str, Any]]: List of open positions
        """
        return [pos for pos in self.positions.values() if pos['status'] == 'OPEN']
    
    def get_position_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get open position for a specific symbol
        
        Args:
            symbol (str): Trading symbol
            
        Returns:
            Optional[Dict[str, Any]]: Position data if found, None otherwise
        """
        for position in self.get_open_positions():
            if position['symbol'] == symbol:
                return position
        return None
    
    def has_open_position(self, symbol: str) -> bool:
        """
        Check if there's an open position for a symbol
        
        Args:
            symbol (str): Trading symbol
            
        Returns:
            bool: True if open position exists
        """
        return self.get_position_by_symbol(symbol) is not None
    
    def calculate_unrealized_pnl(self, symbol: str, current_price: float) -> Optional[Dict[str, float]]:
        """
        Calculate unrealized PnL for an open position
        
        Args:
            symbol (str): Trading symbol
            current_price (float): Current market price
            
        Returns:
            Optional[Dict[str, float]]: PnL data if position exists
        """
        position = self.get_position_by_symbol(symbol)
        
        if not position:
            return None
        
        entry_price = position['entry_price']
        quantity = position['quantity']
        side = position['side']
        leverage = position['leverage']
        
        if side.upper() == 'LONG':
            price_change = current_price - entry_price
        else:  # SHORT
            price_change = entry_price - current_price
        
        unrealized_pnl = (price_change / entry_price) * quantity * entry_price * leverage
        unrealized_pnl_percent = (price_change / entry_price) * 100 * leverage
        
        return {
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pnl_percent': unrealized_pnl_percent,
            'entry_price': entry_price,
            'current_price': current_price
        }
    
    def get_position_summary(self) -> Dict[str, Any]:
        """
        Get summary of all positions
        
        Returns:
            Dict[str, Any]: Position summary statistics
        """
        all_positions = list(self.positions.values())
        closed_positions = [pos for pos in all_positions if pos['status'] == 'CLOSED']
        open_positions = [pos for pos in all_positions if pos['status'] == 'OPEN']
        
        total_pnl = sum(pos['pnl'] for pos in closed_positions)
        winning_trades = len([pos for pos in closed_positions if pos['pnl'] > 0])
        losing_trades = len([pos for pos in closed_positions if pos['pnl'] < 0])
        
        win_rate = (winning_trades / len(closed_positions) * 100) if closed_positions else 0
        
        return {
            'total_positions': len(all_positions),
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'total_pnl': total_pnl,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate
        }
