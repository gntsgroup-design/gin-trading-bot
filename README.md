# Gin Trading Bot

A Python-based derivatives trading bot for Binance USDT-Perpetual pairs using RSI(6) and Bollinger Band strategy.

## Features

- Automated trading on Binance USDT-Perpetual pairs
- RSI(6) and Bollinger Band technical indicators
- 15-minute interval trading strategy
- Configurable parameters per trading pair
- Telegram notifications for position events
- Backtesting functionality with historical data
- Well-documented and maintainable code

## Strategy

The bot implements a long-only strategy:
- Opens long position when RSI(6) < threshold AND price is below Bollinger Band lower band by specified percentage
- Configurable leverage, take profit, and stop loss per pair
- 15-minute candle intervals

## Configuration

Each trading pair can be configured with:
- `leverage`: Trading leverage (e.g., 125)
- `shadow_distance_threshold`: Percentage below BB lower band (e.g., 1.5%)
- `trade_volume`: Position size in USDT (e.g., 20)
- `rsi_long_threshold`: RSI threshold for long entry (e.g., 14)
- `rsi_short_threshold`: RSI threshold for short entry (e.g., 85)
- `take_profit_percent`: Take profit percentage (e.g., 2.0%)
- `stop_loss_percent`: Stop loss percentage (e.g., 1.0%)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your settings in `config/config.json`

3. Add your API keys and Telegram bot token to environment variables or config

4. Run backtest:
```bash
python backtest.py
```

5. Run live trading (when ready):
```bash
python main.py
```

## Backtest

Historical klines data should be placed in `backtest/historical_klines_cache/` directory.
The backtest will analyze the strategy performance across all configured pairs.

## Disclaimer

This bot is for educational purposes. Use at your own risk. Always test thoroughly before live trading.
