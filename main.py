"""
Main Trading Bot Module

This is the main entry point for the trading bot. It orchestrates all components:
- Loads configuration
- Initializes API clients and services
- Runs the main trading loop
- Handles position monitoring and management

The bot operates on a continuous loop, analyzing market data and executing trades
based on the configured strategy.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
import signal

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.api.binance_client import BinanceClient
from src.strategy.trading_strategy import TradingStrategy
from src.notifications.telegram_notifier import TelegramNotifier
from src.position_manager import PositionManager
from dotenv import load_dotenv


class TradingBot:
    """
    Main trading bot class that coordinates all components
    """
    
    def __init__(self, config_path: str = "config/config.json"):
        """
        Initialize the trading bot
        
        Args:
            config_path (str): Path to configuration file
        """
        load_dotenv()
        
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        self.config = self.load_config(config_path)
        
        self.binance_client = None
        self.strategy = None
        self.telegram_notifier = None
        self.position_manager = None
        
        self.running = False
        self.last_analysis_time = {}
        
        self.initialize_components()
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self) -> None:
        """
        Set up logging configuration
        """
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/trading_bot.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from JSON file
        
        Args:
            config_path (str): Path to configuration file
            
        Returns:
            Dict[str, Any]: Configuration data
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            if os.getenv('BINANCE_API_KEY'):
                config['api']['binance_api_key'] = os.getenv('BINANCE_API_KEY')
            if os.getenv('BINANCE_SECRET_KEY'):
                config['api']['binance_secret_key'] = os.getenv('BINANCE_SECRET_KEY')
            if os.getenv('TELEGRAM_BOT_TOKEN'):
                config['telegram']['bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN')
            if os.getenv('TELEGRAM_CHAT_ID'):
                config['telegram']['chat_id'] = os.getenv('TELEGRAM_CHAT_ID')
            if os.getenv('TESTNET'):
                config['api']['testnet'] = os.getenv('TESTNET').lower() == 'true'
            
            self.logger.info(f"Configuration loaded from {config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise
    
    def initialize_components(self) -> None:
        """
        Initialize all bot components
        """
        try:
            api_config = self.config.get('api', {})
            self.binance_client = BinanceClient(
                api_key=api_config.get('binance_api_key', ''),
                secret_key=api_config.get('binance_secret_key', ''),
                testnet=api_config.get('testnet', True)
            )
            
            self.strategy = TradingStrategy(self.config)
            
            telegram_config = self.config.get('telegram', {})
            self.telegram_notifier = TelegramNotifier(
                bot_token=telegram_config.get('bot_token', ''),
                chat_id=telegram_config.get('chat_id', '')
            )
            
            self.position_manager = PositionManager()
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise
    
    def validate_configuration(self) -> bool:
        """
        Validate bot configuration
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            enabled_symbols = self.strategy.get_enabled_symbols()
            
            if not enabled_symbols:
                self.logger.error("No enabled symbols found in configuration")
                return False
            
            for symbol in enabled_symbols:
                is_valid, error_msg = self.strategy.validate_symbol_config(symbol)
                if not is_valid:
                    self.logger.error(f"Invalid configuration for {symbol}: {error_msg}")
                    return False
            
            self.logger.info(f"Configuration validated for {len(enabled_symbols)} symbols")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating configuration: {e}")
            return False
    
    def analyze_market(self) -> List[Dict[str, Any]]:
        """
        Analyze market for all enabled symbols
        
        Returns:
            List[Dict[str, Any]]: Analysis results for all symbols
        """
        results = []
        enabled_symbols = self.strategy.get_enabled_symbols()
        
        for symbol in enabled_symbols:
            try:
                df = self.binance_client.get_klines(
                    symbol=symbol,
                    interval=self.config.get('trading', {}).get('interval', '15m'),
                    limit=100
                )
                
                analysis = self.strategy.analyze_symbol(symbol, df)
                results.append(analysis)
                
                self.last_analysis_time[symbol] = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}")
                results.append({
                    'symbol': symbol,
                    'signal': 'ERROR',
                    'reason': str(e)
                })
        
        return results
    
    def execute_trade(self, analysis: Dict[str, Any]) -> bool:
        """
        Execute a trade based on analysis results
        
        Args:
            analysis (Dict[str, Any]): Analysis results
            
        Returns:
            bool: True if trade executed successfully
        """
        symbol = analysis['symbol']
        signal = analysis['signal']
        
        if signal != 'LONG':
            return False
        
        if self.position_manager.has_open_position(symbol):
            self.logger.info(f"Position already exists for {symbol}, skipping")
            return False
        
        try:
            symbol_config = analysis.get('config', {})
            current_price = analysis['current_price']
            
            leverage = symbol_config.get('leverage', 10)
            self.binance_client.set_leverage(symbol, leverage)
            
            quantity = self.strategy.calculate_position_size(symbol, current_price)
            
            take_profit, stop_loss = self.strategy.calculate_take_profit_stop_loss(
                symbol, current_price, 'LONG'
            )
            
            order = self.binance_client.place_market_order(
                symbol=symbol,
                side='BUY',
                quantity=quantity
            )
            
            position_id = self.position_manager.add_position(
                symbol=symbol,
                side='LONG',
                quantity=quantity,
                entry_price=current_price,
                leverage=leverage,
                take_profit=take_profit,
                stop_loss=stop_loss,
                rsi_at_entry=analysis['rsi']
            )
            
            self.telegram_notifier.notify_position_opened(
                symbol=symbol,
                side='LONG',
                quantity=quantity,
                entry_price=current_price,
                leverage=leverage,
                rsi=analysis['rsi'],
                take_profit=take_profit,
                stop_loss=stop_loss
            )
            
            self.logger.info(f"Trade executed: {symbol} LONG {quantity} @ {current_price}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing trade for {symbol}: {e}")
            self.telegram_notifier.notify_error(f"Trade execution error for {symbol}: {str(e)}")
            return False
    
    def monitor_positions(self) -> None:
        """
        Monitor open positions for exit conditions
        """
        open_positions = self.position_manager.get_open_positions()
        
        for position in open_positions:
            symbol = position['symbol']
            
            try:
                current_price = self.binance_client.get_current_price(symbol)
                
                should_close, reason = self.strategy.should_close_position(
                    symbol, position, current_price
                )
                
                if should_close:
                    self.binance_client.close_position(symbol)
                    
                    updated_position = self.position_manager.close_position(
                        position['id'], current_price, reason
                    )
                    
                    self.telegram_notifier.notify_position_closed(
                        symbol=symbol,
                        side=position['side'],
                        quantity=position['quantity'],
                        entry_price=position['entry_price'],
                        exit_price=current_price,
                        pnl=updated_position['pnl'],
                        pnl_percent=updated_position['pnl_percent'],
                        reason=reason
                    )
                    
                    self.logger.info(f"Position closed: {symbol} - {reason}")
                
            except Exception as e:
                self.logger.error(f"Error monitoring position {symbol}: {e}")
    
    def run_trading_loop(self) -> None:
        """
        Main trading loop
        """
        self.logger.info("Starting trading loop...")
        self.running = True
        
        while self.running:
            try:
                analysis_results = self.analyze_market()
                
                for analysis in analysis_results:
                    if analysis['signal'] == 'LONG':
                        self.execute_trade(analysis)
                
                self.monitor_positions()
                
                summary = self.position_manager.get_position_summary()
                self.logger.info(f"Position summary: {summary}")
                
                time.sleep(60)  # Wait 1 minute between iterations
                
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                time.sleep(30)  # Wait 30 seconds before retrying
    
    def signal_handler(self, signum, frame):
        """
        Handle shutdown signals
        """
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def start(self) -> None:
        """
        Start the trading bot
        """
        try:
            self.logger.info("Starting Gin Trading Bot...")
            
            if not self.validate_configuration():
                raise ValueError("Invalid configuration")
            
            account_info = self.binance_client.get_account_info()
            self.logger.info("API connection successful")
            
            self.run_trading_loop()
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            raise
        finally:
            self.logger.info("Trading bot stopped")


def main():
    """
    Main entry point
    """
    try:
        bot = TradingBot()
        bot.start()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
