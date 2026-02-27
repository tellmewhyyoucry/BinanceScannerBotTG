import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_SECRET = os.getenv('BINANCE_SECRET')
    ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
    
    # Trading Parameters
    MIN_VOLUME = 200_000_000
    MIN_TRADES = 1_000_000
    MAX_BTC_CORRELATION = 0.5
    MIN_WIN_RATE = 0.8
    MIN_RR_RATIO = 2.5
    
    # Monitoring
    SCAN_INTERVAL = 300  # 5 minutes
    MAX_SYMBOLS = 15
    
    # Risk Management
    MAX_RISK_PER_TRADE = 0.01  # 1%
    MIN_STOP_LOSS_PCT = 0.005  # 0.5%
    MAX_STOP_LOSS_PCT = 0.02   # 2%
