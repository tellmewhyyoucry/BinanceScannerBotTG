import asyncio
import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime
from binance import AsyncClient
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import ta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === ЗАМЕНИТЕ ЭТИ ЗНАЧЕНИЯ НА СВОИ ===
TELEGRAM_TOKEN = "8545214216:AAGRz-jmD-2989hx8LuP43Svse9AEC-v1HI"
BINANCE_API_KEY = "lvyzhyX59Jksmwxb5MD6krkfIl3kfAVKWvXokWyGNAUER3KXPQiE0WvWVhH2SBjA"
BINANCE_SECRET = "zjMTHl6MIHLE1RZDsHR1aG29Pamgak2E01mntFAyXsqHPHPhGgCNuRNLVNMKPGo0"
ADMIN_CHAT_ID = "1077455247"
# === КОНЕЦ ЗАМЕНЫ ===

class ImprovedCryptoBot:
    def __init__(self):
        self.binance_client = None
        self.is_scanning = False
        
    async def initialize_binance(self):
        """Инициализация Binance клиента"""
        try:
            self.binance_client = await AsyncClient.create(
                BINANCE_API_KEY, 
                BINANCE_SECRET
            )
            logger.info("Binance client initialized")
            return True
        except Exception as e:
            logger.error(f"Binance init error: {e}")
            return False
    
    async def get_symbols(self):
        """Получает список символов"""
        try:
            if not self.binance_client:
                return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
                
            exchange_info = await self.binance_client.futures_exchange_info()
            symbols = []
            
            for symbol_info in exchange_info['symbols']:
                if (symbol_info['quoteAsset'] == 'USDT' and 
                    symbol_info['status'] == 'TRADING'):
                    symbols.append(symbol_info['symbol'])
            
            return symbols[:10]  # 10 символов для сканирования
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
    
    async def get_price_data(self, symbol, interval='5m', limit=100):
        """Получает данные о цене"""
        try:
            klines = await self.binance_client.futures_klines(
                symbol=symbol, interval=interval, limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
                
            return df
        except Exception as e:
            logger.error(f"Error getting data for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, data):
        """Рассчитывает технические индикаторы"""
        try:
            # RSI
            data['rsi'] = ta.momentum.RSIIndicator(data['close'], window=14).rsi()
            
            # MACD
            macd = ta.trend.MACD(data['close'])
            data['macd'] = macd.macd()
            data['macd_signal'] = macd.macd_signal()
            data['macd_histogram'] = macd.macd_diff()
            
            # Bollinger Bands
            bollinger = ta.volatility.BollingerBands(data['close'], window=20, window_dev=2)
            data['bb_upper'] = bollinger.bollinger_hband()
            data['bb_lower'] = bollinger.bollinger_lband()
            data['bb_middle'] = bollinger.bollinger_mavg()
            
            # Volume SMA
            data['volume_sma'] = data['volume'].rolling(20).mean()
            
            return data
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return data
    
    def analyze_patterns(self, symbol, data):
        """Анализирует данные на наличие различных паттернов"""
        try:
            if len(data) < 50:
                logger.info(f"Not enough data for {symbol}")
                return None
            
            data = self.calculate_indicators(data)
            current = data.iloc[-1]
            prev = data.iloc[-2]
            
            setups = []
            
            # 1. Пробой Bollinger Band
            if current['close'] > current['bb_upper'] and prev['close'] <= prev['bb_upper']:
                logger.info(f"{symbol}: Bollinger Breakout detected")
                entry = current['close']
                stop_loss = current['bb_middle']
                take_profit = entry + (entry - stop_loss) * 1.5
                
                setups.append({
                    'symbol': symbol,
                    'pattern': 'Bollinger Breakout',
                    'entry': round(entry, 4),
                    'stop_loss': round(stop_loss, 4),
                    'take_profit': round(take_profit, 4),
                    'timestamp': datetime.now(),
                    'confidence': 'medium'
                })
            
            # 2. RSI перепроданность/перекупленность
            if current['rsi'] < 30 and prev['rsi'] >= 30:  # Перепроданность
                logger.info(f"{symbol}: RSI Oversold detected")
                entry = current['close']
                stop_loss = entry * 0.98
                take_profit = entry * 1.03
                
                setups.append({
                    'symbol': symbol,
                    'pattern': 'RSI Oversold Bounce',
                    'entry': round(entry, 4),
                    'stop_loss': round(stop_loss, 4),
                    'take_profit': round(take_profit, 4),
                    'timestamp': datetime.now(),
                    'confidence': 'medium'
                })
            
            # 3. MACD пересечение
            if (current['macd'] > current['macd_signal'] and 
                prev['macd'] <= prev['macd_signal']):
                logger.info(f"{symbol}: MACD Bullish Cross detected")
                entry = current['close']
                stop_loss = entry * 0.99
                take_profit = entry * 1.02
                
                setups.append({
                    'symbol': symbol,
                    'pattern': 'MACD Bullish Cross',
                    'entry': round(entry, 4),
                    'stop_loss': round(stop_loss, 4),
                    'take_profit': round(take_profit, 4),
                    'timestamp': datetime.now(),
                    'confidence': 'medium'
                })
            
            # 4. Объемный всплеск
            volume_ratio = current['volume'] / current['volume_sma']
            if volume_ratio > 2.0 and current['close'] > prev['close']:
                logger.info(f"{symbol}: Volume Spike detected ({volume_ratio:.1f}x)")
                entry = current['close']
                stop_loss = entry * 0.985
                take_profit = entry * 1.025
                
                setups.append({
                    'symbol': symbol,
                    'pattern': f'Volume Spike ({volume_ratio:.1f}x)',
                    'entry': round(entry, 4),
                    'stop_loss': round(stop_loss, 4),
                    'take_profit': round(take_profit, 4),
                    'timestamp': datetime.now(),
                    'confidence': 'high'
                })
            
            return setups if setups else None
                
        except Exception as e:
            logger.error(f"Analysis error for {symbol}: {e}")
            
        return None
    
    async def send_alert(self, chat_id, setup):
        """Отправляет алерт в Telegram"""
        try:
            message = f"""
TRADING SIGNAL 🚀

Coin: {setup['symbol']}
Pattern: {setup['pattern']}
Confidence: {setup['confidence'].upper()}

Entry: {setup['entry']}
Stop Loss: {setup['stop_loss']}
Take Profit: {setup['take_profit']}

Potential Profit: {((setup['take_profit'] - setup['entry']) / setup['entry'] * 100):.2f}%
Risk: {((setup['entry'] - setup['stop_loss']) / setup['entry'] * 100):.2f}%

Time: {setup['timestamp'].strftime('%H:%M:%S')}
"""
            
            from telegram import Bot
            temp_bot = Bot(token=TELEGRAM_TOKEN)
            await temp_bot.send_message(chat_id=chat_id, text=message)
            await temp_bot.close()
            
            logger.info(f"Alert sent for {setup['symbol']} - {setup['pattern']}")
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def scan_market(self, chat_id):
        """Сканирует рынок"""
        try:
            symbols = await self.get_symbols()
            logger.info(f"Scanning {len(symbols)} symbols")
            
            total_setups = 0
            for symbol in symbols:
                try:
                    data = await self.get_price_data(symbol)
                    if data.empty:
                        logger.info(f"No data for {symbol}")
                        continue
                    
                    logger.info(f"Analyzing {symbol} - Price: {data['close'].iloc[-1]:.4f}")
                    setups = self.analyze_patterns(symbol, data)
                    
                    if setups:
                        for setup in setups:
                            await self.send_alert(chat_id, setup)
                            total_setups += 1
                            await asyncio.sleep(1)  # Пауза между сообщениями
                    else:
                        logger.info(f"No setups found for {symbol}")
                        
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")
                    continue
            
            logger.info(f"Scan completed. Found {total_setups} setups.")
                    
        except Exception as e:
            logger.error(f"Market scan error: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        chat_id = update.effective_chat.id
        await update.message.reply_text(
            "🚀 Improved Crypto Scanner Bot started!\n\n"
            "I will scan for:\n"
            "• Bollinger Breakouts\n"
            "• RSI Oversold Conditions\n" 
            "• MACD Crossovers\n"
            "• Volume Spikes\n\n"
            "Starting market scan..."
        )
        logger.info(f"Bot started by user {chat_id}")
        
        # Запускаем сканирование
        self.is_scanning = True
        asyncio.create_task(self.continuous_scan(chat_id))
    
    async def continuous_scan(self, chat_id):
        """Непрерывное сканирование"""
        scan_count = 0
        while self.is_scanning:
            try:
                scan_count += 1
                logger.info(f"=== Scan #{scan_count} ===")
                await self.scan_market(chat_id)
                logger.info(f"Waiting 2 minutes for next scan...")
                await asyncio.sleep(120)  # Сканируем каждые 2 минуты
            except Exception as e:
                logger.error(f"Scanning error: {e}")
                await asyncio.sleep(30)
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stop"""
        self.is_scanning = False
        await update.message.reply_text("Scanning stopped. Use /start to resume.")
        logger.info("Bot stopped by user")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        status = "active" if self.is_scanning else "inactive"
        await update.message.reply_text(f"Bot status: {status}\nUse /start to begin scanning.")

def main():
    """Главная функция"""
    logger.info("Starting Improved Crypto Bot...")
    
    # Создаем бота
    bot = ImprovedCryptoBot()
    
    # Создаем приложение Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("stop", bot.stop_command))
    application.add_handler(CommandHandler("status", bot.status_command))
    
    # Функция инициализации при запуске
    async def init_app():
        await bot.initialize_binance()
        return application
    
    # Запускаем бота
    try:
        logger.info("Starting Telegram polling...")
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    main()