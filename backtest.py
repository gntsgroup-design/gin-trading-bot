"""
Backtesting Module

This module implements backtesting functionality for the trading strategy:
- Loads historical klines data from cache
- Simulates trading strategy execution
- Calculates performance metrics
- Generates backtest reports

The backtest uses the same strategy logic as the live bot but operates on historical data.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.strategy.trading_strategy import TradingStrategy
from src.indicators.technical_indicators import TechnicalIndicators


class Backtester:
    """
    Backtesting engine for the trading strategy
    """
    
    def __init__(self, config_path: str = "config/config.json", 
                 data_dir: str = "backtest/historical_klines_cache"):
        """
        Initialize backtester
        
        Args:
            config_path (str): Path to configuration file
            data_dir (str): Directory containing historical data
        """
        self.config_path = config_path
        self.data_dir = data_dir
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.config = self.load_config()
        
        self.strategy = TradingStrategy(self.config)
        
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        
        self.metrics = {}
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from JSON file
        
        Returns:
            Dict[str, Any]: Configuration data
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            self.logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise
    
    def load_historical_data(self, symbol: str) -> pd.DataFrame:
        """
        Load historical klines data for a symbol
        
        Args:
            symbol (str): Trading symbol
            
        Returns:
            pd.DataFrame: Historical OHLCV data
        """
        possible_files = [
            f"{symbol}_15m.csv",
            f"{symbol}_klines.csv",
            f"{symbol}.csv",
            f"{symbol}_15m.json",
            f"{symbol}.json"
        ]
        
        for filename in possible_files:
            filepath = os.path.join(self.data_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    if filename.endswith('.csv'):
                        df = pd.read_csv(filepath)
                    elif filename.endswith('.json'):
                        df = pd.read_json(filepath)
                    else:
                        continue
                    
                    df = self.standardize_dataframe(df)
                    
                    if len(df) > 0:
                        self.logger.info(f"Loaded {len(df)} records for {symbol} from {filename}")
                        return df
                        
                except Exception as e:
                    self.logger.warning(f"Error loading {filepath}: {e}")
                    continue
        
        self.logger.warning(f"No historical data found for {symbol}, creating sample data")
        return self.create_sample_data(symbol)
    
    def standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize DataFrame column names and data types
        
        Args:
            df (pd.DataFrame): Raw DataFrame
            
        Returns:
            pd.DataFrame: Standardized DataFrame
        """
        column_mappings = {
            'timestamp': 'timestamp',
            'open_time': 'timestamp',
            'time': 'timestamp',
            'datetime': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        }
        
        df_columns_lower = {col: col.lower() for col in df.columns}
        
        for old_name, new_name in column_mappings.items():
            if old_name in df_columns_lower.values():
                original_col = [k for k, v in df_columns_lower.items() if v == old_name][0]
                df = df.rename(columns={original_col: new_name})
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in data")
        
        for col in required_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if 'timestamp' in df.columns:
            if df['timestamp'].dtype == 'object':
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                except:
                    try:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    except:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            elif df['timestamp'].dtype in ['int64', 'float64']:
                if df['timestamp'].max() > 1e10:  # Milliseconds
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                else:  # Seconds
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        else:
            df['timestamp'] = pd.date_range(
                start='2023-01-01', periods=len(df), freq='15T'
            )
        
        df.set_index('timestamp', inplace=True)
        
        df = df.dropna()
        
        df = df.sort_index()
        
        return df[required_columns]
    
    def create_sample_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """
        Create sample historical data for demonstration
        
        Args:
            symbol (str): Trading symbol
            days (int): Number of days of data to create
            
        Returns:
            pd.DataFrame: Sample OHLCV data
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        timestamps = pd.date_range(start=start_date, end=end_date, freq='15T')
        
        np.random.seed(42)  # For reproducible results
        
        if 'BTC' in symbol:
            base_price = 45000
        elif 'ETH' in symbol:
            base_price = 3000
        elif 'BNB' in symbol:
            base_price = 300
        else:
            base_price = 100
        
        returns = np.random.normal(0, 0.002, len(timestamps))  # 0.2% volatility per 15min
        prices = [base_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)
        
        data = []
        for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
            volatility = abs(np.random.normal(0, 0.001))  # Intrabar volatility
            
            high = close * (1 + volatility)
            low = close * (1 - volatility)
            
            if i == 0:
                open_price = close
            else:
                open_price = prices[i-1]
            
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = np.random.uniform(1000, 10000)  # Random volume
            
            data.append({
                'timestamp': timestamp,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        self.logger.info(f"Created {len(df)} sample records for {symbol}")
        return df[['open', 'high', 'low', 'close', 'volume']]
    
    def run_backtest(self, symbol: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Run backtest for a single symbol
        
        Args:
            symbol (str): Trading symbol
            df (pd.DataFrame): Historical data
            
        Returns:
            List[Dict[str, Any]]: List of trades
        """
        trades = []
        position = None
        
        symbol_config = self.config.get('pairs', {}).get(symbol, {})
        if not symbol_config or not symbol_config.get('enabled', False):
            self.logger.warning(f"Symbol {symbol} not configured or disabled")
            return trades
        
        self.logger.info(f"Running backtest for {symbol} with {len(df)} data points")
        
        for i in range(max(20, 6), len(df)):  # Start after enough data for indicators
            current_data = df.iloc[:i+1]
            current_time = df.index[i]
            
            analysis = self.strategy.analyze_symbol(symbol, current_data)
            
            if position is None:  # No open position
                if analysis['signal'] == 'LONG':
                    entry_price = analysis['current_price']
                    quantity = self.strategy.calculate_position_size(symbol, entry_price)
                    take_profit, stop_loss = self.strategy.calculate_take_profit_stop_loss(
                        symbol, entry_price, 'LONG'
                    )
                    
                    position = {
                        'symbol': symbol,
                        'side': 'LONG',
                        'entry_time': current_time,
                        'entry_price': entry_price,
                        'quantity': quantity,
                        'take_profit': take_profit,
                        'stop_loss': stop_loss,
                        'rsi_at_entry': analysis['rsi'],
                        'leverage': symbol_config.get('leverage', 10)
                    }
                    
                    self.logger.debug(f"Opened position: {symbol} LONG @ {entry_price}")
            
            else:  # Position is open
                current_price = analysis['current_price']
                
                should_close = False
                exit_reason = None
                
                if position['side'] == 'LONG':
                    if current_price >= position['take_profit']:
                        should_close = True
                        exit_reason = 'Take Profit'
                    elif current_price <= position['stop_loss']:
                        should_close = True
                        exit_reason = 'Stop Loss'
                
                if should_close:
                    exit_price = current_price
                    
                    if position['side'] == 'LONG':
                        price_change = exit_price - position['entry_price']
                    else:
                        price_change = position['entry_price'] - exit_price
                    
                    pnl_percent = (price_change / position['entry_price']) * 100 * position['leverage']
                    pnl_usdt = (price_change / position['entry_price']) * symbol_config.get('trade_volume', 20) * position['leverage']
                    
                    trade = {
                        'symbol': symbol,
                        'side': position['side'],
                        'entry_time': position['entry_time'],
                        'exit_time': current_time,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'quantity': position['quantity'],
                        'leverage': position['leverage'],
                        'rsi_at_entry': position['rsi_at_entry'],
                        'pnl_percent': pnl_percent,
                        'pnl_usdt': pnl_usdt,
                        'exit_reason': exit_reason,
                        'duration_minutes': (current_time - position['entry_time']).total_seconds() / 60
                    }
                    
                    trades.append(trade)
                    position = None
                    
                    self.logger.debug(f"Closed position: {symbol} {exit_reason} @ {exit_price} - PnL: {pnl_percent:.2f}%")
        
        self.logger.info(f"Backtest completed for {symbol}: {len(trades)} trades")
        return trades
    
    def run_full_backtest(self) -> Dict[str, Any]:
        """
        Run backtest for all enabled symbols
        
        Returns:
            Dict[str, Any]: Backtest results
        """
        self.logger.info("Starting full backtest...")
        
        all_trades = []
        symbol_results = {}
        
        enabled_symbols = self.strategy.get_enabled_symbols()
        
        if not enabled_symbols:
            self.logger.error("No enabled symbols found in configuration")
            return {}
        
        for symbol in enabled_symbols:
            try:
                df = self.load_historical_data(symbol)
                
                if df.empty:
                    self.logger.warning(f"No data available for {symbol}")
                    continue
                
                trades = self.run_backtest(symbol, df)
                all_trades.extend(trades)
                
                symbol_metrics = self.calculate_symbol_metrics(trades)
                symbol_results[symbol] = {
                    'trades': trades,
                    'metrics': symbol_metrics
                }
                
            except Exception as e:
                self.logger.error(f"Error backtesting {symbol}: {e}")
                continue
        
        overall_metrics = self.calculate_overall_metrics(all_trades)
        
        results = {
            'overall_metrics': overall_metrics,
            'symbol_results': symbol_results,
            'all_trades': all_trades,
            'config': self.config
        }
        
        self.logger.info(f"Backtest completed: {len(all_trades)} total trades across {len(symbol_results)} symbols")
        return results
    
    def calculate_symbol_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate performance metrics for a symbol
        
        Args:
            trades (List[Dict[str, Any]]): List of trades
            
        Returns:
            Dict[str, Any]: Performance metrics
        """
        if not trades:
            return {}
        
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t['pnl_percent'] > 0])
        losing_trades = len([t for t in trades if t['pnl_percent'] < 0])
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl_usdt'] for t in trades)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        winning_pnl = [t['pnl_usdt'] for t in trades if t['pnl_usdt'] > 0]
        losing_pnl = [t['pnl_usdt'] for t in trades if t['pnl_usdt'] < 0]
        
        avg_win = sum(winning_pnl) / len(winning_pnl) if winning_pnl else 0
        avg_loss = sum(losing_pnl) / len(losing_pnl) if losing_pnl else 0
        
        profit_factor = abs(sum(winning_pnl) / sum(losing_pnl)) if losing_pnl else float('inf')
        
        durations = [t['duration_minutes'] for t in trades]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_duration_minutes': avg_duration
        }
    
    def calculate_overall_metrics(self, all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate overall portfolio metrics
        
        Args:
            all_trades (List[Dict[str, Any]]): All trades across symbols
            
        Returns:
            Dict[str, Any]: Overall metrics
        """
        if not all_trades:
            return {}
        
        symbol_metrics = self.calculate_symbol_metrics(all_trades)
        
        symbols_traded = len(set(t['symbol'] for t in all_trades))
        
        daily_returns = []
        if all_trades:
            trades_by_date = {}
            for trade in all_trades:
                date = trade['exit_time'].date()
                if date not in trades_by_date:
                    trades_by_date[date] = []
                trades_by_date[date].append(trade['pnl_usdt'])
            
            for date, pnls in trades_by_date.items():
                daily_returns.append(sum(pnls))
        
        if daily_returns:
            avg_daily_return = np.mean(daily_returns)
            std_daily_return = np.std(daily_returns)
            sharpe_ratio = avg_daily_return / std_daily_return if std_daily_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        symbol_metrics.update({
            'symbols_traded': symbols_traded,
            'sharpe_ratio': sharpe_ratio,
            'total_trading_days': len(daily_returns) if daily_returns else 0
        })
        
        return symbol_metrics
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """
        Generate a text report of backtest results
        
        Args:
            results (Dict[str, Any]): Backtest results
            
        Returns:
            str: Formatted report
        """
        if not results:
            return "No backtest results available"
        
        overall_metrics = results.get('overall_metrics', {})
        symbol_results = results.get('symbol_results', {})
        
        report = []
        report.append("=" * 60)
        report.append("GIN TRADING BOT - BACKTEST REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        report.append("OVERALL PERFORMANCE")
        report.append("-" * 30)
        report.append(f"Total Trades: {overall_metrics.get('total_trades', 0)}")
        report.append(f"Symbols Traded: {overall_metrics.get('symbols_traded', 0)}")
        report.append(f"Win Rate: {overall_metrics.get('win_rate', 0):.2f}%")
        report.append(f"Total PnL: ${overall_metrics.get('total_pnl', 0):.2f}")
        report.append(f"Average PnL per Trade: ${overall_metrics.get('avg_pnl', 0):.2f}")
        report.append(f"Profit Factor: {overall_metrics.get('profit_factor', 0):.2f}")
        report.append(f"Sharpe Ratio: {overall_metrics.get('sharpe_ratio', 0):.2f}")
        report.append("")
        
        report.append("SYMBOL BREAKDOWN")
        report.append("-" * 30)
        
        for symbol, data in symbol_results.items():
            metrics = data['metrics']
            trades = data['trades']
            
            report.append(f"\n{symbol}:")
            report.append(f"  Trades: {metrics.get('total_trades', 0)}")
            report.append(f"  Win Rate: {metrics.get('win_rate', 0):.2f}%")
            report.append(f"  Total PnL: ${metrics.get('total_pnl', 0):.2f}")
            report.append(f"  Avg Duration: {metrics.get('avg_duration_minutes', 0):.1f} minutes")
        
        all_trades = results.get('all_trades', [])
        if all_trades:
            report.append("\nRECENT TRADES (Last 10)")
            report.append("-" * 30)
            
            recent_trades = sorted(all_trades, key=lambda x: x['exit_time'], reverse=True)[:10]
            
            for trade in recent_trades:
                report.append(
                    f"{trade['symbol']} {trade['side']} | "
                    f"Entry: ${trade['entry_price']:.4f} | "
                    f"Exit: ${trade['exit_price']:.4f} | "
                    f"PnL: {trade['pnl_percent']:+.2f}% | "
                    f"{trade['exit_reason']}"
                )
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
    
    def save_results(self, results: Dict[str, Any], output_dir: str = "backtest/results") -> None:
        """
        Save backtest results to files
        
        Args:
            results (Dict[str, Any]): Backtest results
            output_dir (str): Output directory
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        json_file = os.path.join(output_dir, f"backtest_results_{timestamp}.json")
        with open(json_file, 'w') as f:
            json_results = self.convert_datetime_to_string(results)
            json.dump(json_results, f, indent=2, default=str)
        
        report = self.generate_report(results)
        report_file = os.path.join(output_dir, f"backtest_report_{timestamp}.txt")
        with open(report_file, 'w') as f:
            f.write(report)
        
        self.logger.info(f"Results saved to {output_dir}")
        print(f"Results saved to:")
        print(f"  JSON: {json_file}")
        print(f"  Report: {report_file}")
    
    def convert_datetime_to_string(self, obj):
        """
        Convert datetime objects to strings for JSON serialization
        """
        if isinstance(obj, dict):
            return {k: self.convert_datetime_to_string(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_datetime_to_string(item) for item in obj]
        elif isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        else:
            return obj


def main():
    """
    Main entry point for backtesting
    """
    print("Starting Gin Trading Bot Backtest...")
    
    try:
        backtester = Backtester()
        
        results = backtester.run_full_backtest()
        
        if not results:
            print("No backtest results generated")
            return
        
        report = backtester.generate_report(results)
        print("\n" + report)
        
        backtester.save_results(results)
        
        print("\nBacktest completed successfully!")
        
    except Exception as e:
        print(f"Error running backtest: {e}")
        logging.error(f"Backtest error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
