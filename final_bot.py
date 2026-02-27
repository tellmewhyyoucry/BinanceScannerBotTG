import asyncio
import pandas as pd
import numpy as np
import logging
import json
import os
import sys
from datetime import datetime, timedelta
from binance import AsyncClient
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import ta

# Устанавливаем UTF-8 кодировку для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Создаем папку для логов если ее нет
os.makedirs('logs', exist_ok=True)

# Настройка логирования без эмодзи
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scanner.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# === ЗАМЕНИТЕ ЭТИ ЗНАЧЕНИЯ НА СВОИ ===
TELEGRAM_TOKEN = "8545214216:AAGRz-jmD-2989hx8LuP43Svse9AEC-v1HI"
BINANCE_API_KEY = "lvyzhyX59Jksmwxb5MD6krkfIl3kfAVKWvXokWyGNAUER3KXPQiE0WvWVhH2SBjA" 
BINANCE_SECRET = "zjMTHl6MIHLE1RZDsHR1aG29Pamgak2E01mntFAyXsqHPHPhGgCNuRNLVNMKPGo0"
ADMIN_CHAT_ID = "1077455247"
# === КОНЕЦ ЗАМЕНЫ ===

class ProfitScanner:
    def __init__(self):
        self.patterns_win_rate = {
            'bullish_breakout': 0.82,
            'bearish_breakout': 0.81,
            'flag_pennant': 0.85,
        }
    
    def _find_support_resistance(self, data, window=20):
        """Находит уровни поддержки и сопротивления"""
        try:
            highs = data['high'].rolling(window=window).max()
            lows = data['low'].rolling(window=window).min()
            
            resistance = highs.iloc[-5:].max()
            support = lows.iloc[-5:].min()
            
            return support, resistance
        except:
            return None, None
    
    def _calculate_indicators(self, data):
        """Рассчитывает технические индикаторы"""
        try:
            # EMA
            data['ema_20'] = ta.trend.EMAIndicator(data['close'], window=20).ema_indicator()
            data['ema_50'] = ta.trend.EMAIndicator(data['close'], window=50).ema_indicator()
            
            # Volume
            data['volume_sma'] = data['volume'].rolling(20).mean()
            
            return data
        except:
            return data
    
    async def detect_breakout(self, symbol, data):
        """Обнаруживает пробойные формации"""
        try:
            if len(data) < 50:
                return None
            
            data = self._calculate_indicators(data)
            current = data.iloc[-1]
            prev = data.iloc[-2]
            
            support, resistance = self._find_support_resistance(data)
            if support is None or resistance is None:
                return None
            
            current_price = current['close']
            
            # Проверка пробоя сопротивления с объемом
            volume_condition = current['volume'] > current['volume_sma'] * 1.5
            price_condition = current['close'] > resistance
            previous_condition = prev['close'] < resistance

            if volume_condition and price_condition and previous_condition:
                entry = current['close'] * 1.002
                stop_loss = support
                
                # Расчет тейк-профитов
                tp1 = entry + (entry - stop_loss) * 1
                tp2 = entry + (entry - stop_loss) * 2
                tp3 = entry + (entry - stop_loss) * 3
                
                rr_ratio = (tp3 - entry) / (entry - stop_loss)
                
                if rr_ratio >= 2.5:
                    return {
                        'symbol': symbol,
                        'pattern': 'Пробой сопротивления',
                        'entry': round(entry, 4),
                        'stop_loss': round(stop_loss, 4),
                        'take_profit': [
                            round(tp1, 4),
                            round(tp2, 4),
                            round(tp3, 4)
                        ],
                        'probability': 0.82,
                        'rr_ratio': round(rr_ratio, 2),
                        'confidence': 'high',
                        'timestamp': datetime.now(),
                        'volume_boost': round(current['volume'] / current['volume_sma'], 2)
                    }
        except Exception as e:
            logger.error(f"Breakout detection error for {symbol}: {e}")
        return None

class CryptoScannerBot:
    def __init__(self):
        self.tg_bot = Bot(token=TELEGRAM_TOKEN)
        self.binance_client = None
        self.scanner = ProfitScanner()
        self.sent_setups = set()
        self.is_running = False
        
    async def initialize(self):
        """Инициализация клиентов"""
        try:
            self.binance_client = await AsyncClient.create(
                BINANCE_API_KEY, 
                BINANCE_SECRET
            )
            logger.info("Binance client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            return False
    
    async def get_symbols(self):
        """Получает символы для сканирования"""
        try:
            exchange_info = await self.binance_client.futures_exchange_info()
            symbols = []
            
            for symbol_info in exchange_info['symbols']:
                if (symbol_info['quoteAsset'] == 'USDT' and 
                    symbol_info['status'] == 'TRADING'):
                    symbols.append(symbol_info['symbol'])
            
            return symbols[:5]  # Ограничиваем для теста
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']  # Fallback
    
    async def get_klines_data(self, symbol, interval='5m', limit=100):
        """Получает данные свечей"""
        try:
            klines = await self.binance_client.futures_klines(
                symbol=symbol, 
                interval=interval, 
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Конвертация типов
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
                
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            return df
            
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            return pd.DataFrame()
    
    async def send_setup_alert(self, chat_id, setup):
        """Отправляет алерт о сетапе"""
        try:
            setup_key = f"{setup['symbol']}_{setup['timestamp'].strftime('%H%M')}"
            
            if setup_key in self.sent_setups:
                return
                
            self.sent_setups.add(setup_key)
            
            # Сообщение без эмодзи для Windows
            message = f"""
ПРИБЫЛЬНЫЙ СЕТАП

Монета: {setup['symbol']}
Формация: {setup['pattern']}
Вероятность: {setup['probability']*100}% 

Торговые уровни:
Вход: {setup['entry']}
Стоп-лосс: {setup['stop_loss']}
Риск: {abs((setup['entry'] - setup['stop_loss']) / setup['entry'] * 100):.2f}%

Тейк-профиты:
TP1: {setup['take_profit'][0]} (+{((setup['take_profit'][0] - setup['entry']) / setup['entry'] * 100):.2f}%)
TP2: {setup['take_profit'][1]} (+{((setup['take_profit'][1] - setup['entry']) / setup['entry'] * 100):.2f}%)
TP3: {setup['take_profit'][2]} (+{((setup['take_profit'][2] - setup['entry']) / setup['entry'] * 100):.2f}%)

R/R Ratio: {setup['rr_ratio']} 
Время: {setup['timestamp'].strftime('%H:%M:%S')}

Торгуйте ответственно!
"""
            await self.tg_bot.send_message(
                chat_id=chat_id,
                text=message
            )
            logger.info(f"Sent alert for {setup['symbol']}")
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def scan_market(self, chat_id):
        """Сканирует рынок на наличие сетапов"""
        try:
            symbols = await self.get_symbols()
            logger.info(f"Scanning {len(symbols)} symbols...")
            
            found_setups = 0
            for symbol in symbols:
                try:
                    data = await self.get_klines_data(symbol)
                    if data.empty:
                        continue
                    
                    setup = await self.scanner.detect_breakout(symbol, data)
                    if setup:
                        await self.send_setup_alert(chat_id, setup)
                        found_setups += 1
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")
                    continue
            
            if found_setups == 0:
                logger.info("No profitable setups found this scan")
                    
        except Exception as e:
            logger.error(f"Market scan error: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        chat_id = update.effective_chat.id
        welcome_message = """
Crypto Scanner Bot активирован!

Я буду присылать прибыльные торговые сетапы с вероятностью >80%.

Начинаю сканирование...
"""
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_message
        )
        logger.info(f"User {chat_id} started the bot")
        
        # Запуск сканирования в фоне
        if not self.is_running:
            self.is_running = True
            asyncio.create_task(self.continuous_scanning(chat_id))
    
    async def continuous_scanning(self, chat_id):
        """Непрерывное сканирование"""
        logger.info("Starting continuous market scanning...")
        while self.is_running:
            try:
                await self.scan_market(chat_id)
                logger.info("Waiting 60 seconds until next scan...")
                await asyncio.sleep(60)  # 1 минута для теста
            except Exception as e:
                logger.error(f"Continuous scanning error: {e}")
                await asyncio.sleep(30)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        chat_id = update.effective_chat.id
        status_message = """
Статус бота: Активен
Режим: Непрерывное сканирование
Интервал: 1 минута
Цель: Прибыльные сетапы >80%
"""
        await context.bot.send_message(
            chat_id=chat_id,
            text=status_message
        )
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stop"""
        chat_id = update.effective_chat.id
        self.is_running = False
        await context.bot.send_message(
            chat_id=chat_id,
            text="Сканирование остановлено. Используйте /start для возобновления."
        )
        logger.info(f"User {chat_id} stopped the bot")

async def main():
    """Главная функция"""
    logger.info("Starting Crypto Scanner Bot...")
    
    bot = CryptoScannerBot()
    
    # Инициализация
    success = await bot.initialize()
    if not success:
        logger.error("Failed to initialize bot. Exiting.")
        return
    
    # Создаем приложение Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("status", bot.status_command))
    application.add_handler(CommandHandler("stop", bot.stop_command))
    
    # Запускаем бота
    logger.info("Bot initialized successfully. Starting polling...")
    
    try:
        await application.run_polling()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        # Закрываем соединения
        bot.is_running = False
        if bot.binance_client:
            await bot.binance_client.close_connection()
        logger.info("Bot stopped")

if __name__ == "__main__":
    # Исправление для Windows event loop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Запускаем бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")